"""Serveur local de Stencil Studio (stencil_studio/server.py) : seule sa page peut l'appeler. Un autre site
ouvert dans un navigateur n'a ni le bon nom d'hôte ni le jeton de la page."""
import http.client
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

try:
    from stencil_studio import server
except ImportError:  # dépendances de Stencil Studio absentes
    server = None


@unittest.skipIf(server is None, "Stencil Studio non importable ici")
class ServerSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv, cls.port = server.start_server(0)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def request(self, method, path, host=None, token=None, body=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        headers = {"Host": host or f"127.0.0.1:{self.port}"}
        if token:
            headers["X-Stencil-Token"] = token
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        data = response.read()
        connection.close()
        return response.status, data

    def test_the_page_carries_the_token(self):
        status, page = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(server.TOKEN.encode(), page)
        self.assertNotIn(b"__STENCIL_TOKEN__", page)

    def test_api_needs_the_token(self):
        self.assertEqual(self.request("GET", "/api/langs")[0], 403)
        self.assertEqual(self.request("GET", "/api/langs", token="faux")[0], 403)
        self.assertEqual(self.request("GET", "/api/langs", token=server.TOKEN)[0], 200)
        self.assertEqual(self.request("GET", f"/api/langs?t={server.TOKEN}")[0], 200)    # image : paramètre t

    def test_writes_from_another_site_are_refused(self):
        self.assertEqual(self.request("POST", "/api/presets", body=b"{}")[0], 403)

    def test_a_foreign_host_name_is_refused_even_with_the_token(self):
        """« DNS rebinding » : un site fait pointer son nom vers 127.0.0.1 ; le nom d'hôte le trahit."""
        self.assertEqual(self.request("GET", "/", host=f"evil.example:{self.port}")[0], 403)
        self.assertEqual(self.request("GET", "/api/langs", host="evil.example", token=server.TOKEN)[0], 403)


if __name__ == "__main__":
    unittest.main()

"""Boîte de dialogue « Rejoindre la communauté WhatsApp ».

Utilisation :

    from laser_studio.ui.community import CommunityDialog

    CommunityDialog(self).exec()
"""

from laser_studio.ui.community.dialog import COMMUNITY_URL, CommunityDialog

__all__ = ["COMMUNITY_URL", "CommunityDialog"]

// Pied de page du guide en PDF (ajouté par pdf.yaml) : titre à gauche, logiciel au centre, page / total à droite.
#set page(footer: context [
  #set text(size: 8pt, fill: luma(110))
  #grid(
    columns: (1fr, auto, 1fr),
    align(left)[Guide de démarrage],
    align(center)[Laser Studio Pro],
    align(right)[#counter(page).display("1 / 1", both: true)],
  )
])

// Certificate template. Exports render(record).
// Expected record fields: name (str), course (str), date (str).
#let render(record) = {
  set page(paper: "a4", margin: 0pt)
  set align(center)

  pad(x: 2cm, y: 2.5cm)[
    #rect(width: 100%, height: 100%, stroke: 2pt + rgb("#b08d2e"), inset: 1.2cm)[
      #v(1.2cm)
      #text(size: 14pt, tracking: 4pt, fill: rgb("#b08d2e"))[CERTIFICATE OF COMPLETION]
      #v(0.4cm)
      #line(length: 30%, stroke: 1pt + rgb("#b08d2e"))
      #v(1.4cm)
      #text(size: 11pt, fill: gray)[This certifies that]
      #v(0.6cm)
      #text(size: 34pt, weight: "bold")[#record.name]
      #v(0.8cm)
      #text(size: 11pt, fill: gray)[has successfully completed]
      #v(0.4cm)
      #text(size: 18pt, weight: "bold", fill: rgb("#1f3a5f"))[#record.course]
      #v(1.4cm)
      #grid(
        columns: (1fr, 1fr),
        column-gutter: 2cm,
        align(center)[
          #line(length: 50%, stroke: 0.5pt + black)
          #v(0.2em)
          #text(size: 9pt)[#record.date]
        ],
        align(center)[
          #line(length: 50%, stroke: 0.5pt + black)
          #v(0.2em)
          #text(size: 9pt)[Acme Academy]
        ],
      )
    ]
  ]
}

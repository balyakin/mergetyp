// Invoice template. Exports render(record).
// Uses record.at(...) for access. Fields:
//   invoice_id (str), date (str), client (str), email (str),
//   items (array of {description, qty, price}),
//   subtotal (num), tax (num), total (num).
#let money(n) = "$" + str(n)

#let render(record) = {
  set page(
    paper: "a4",
    margin: (x: 2cm, top: 2.2cm, bottom: 1.6cm),
  )
  set text(size: 10.5pt)

  [
    #align(right, text(size: 9pt, fill: gray)[
      Invoice #record.at("invoice_id") · #record.at("date")
    ])
    #v(0.8cm)

    #grid(
      columns: (1fr, 1fr),
      column-gutter: 1.5cm,
      [
        #text(size: 16pt, weight: "bold", fill: rgb("#1f3a5f"))[Acme Co.]
        #v(0.3em)
        #text(size: 9pt, fill: gray)[
          123 Market Street \
          San Francisco, CA 94103 \
          billing\@acme.example
        ]
      ],
      align(right)[
        #text(size: 9pt, fill: gray)[BILLED TO]
        #v(0.3em)
        #text(size: 12pt, weight: "bold")[#record.at("client")]
        #text(size: 9pt, fill: gray)[#record.at("email")]
      ],
    )

    #v(1.2cm)

    #let items = record.at("items")
    #table(
      columns: (1fr, 2.2cm, 2.5cm, 2.5cm),
      align: (left, right, right, right),
      stroke: none,
      table.header(
        table.cell(fill: rgb("#1f3a5f"))[#text(white, weight: "bold")[Description]],
        table.cell(fill: rgb("#1f3a5f"))[#text(white, weight: "bold")[Qty]],
        table.cell(fill: rgb("#1f3a5f"))[#text(white, weight: "bold")[Unit Price]],
        table.cell(fill: rgb("#1f3a5f"))[#text(white, weight: "bold")[Amount]],
      ),
      ..items.map(it => (
        [#it.at("description")],
        [#text(rgb("#444"))[#it.at("qty")]],
        [#text(rgb("#444"))[#money(it.at("price"))]],
        [#money(it.at("qty") * it.at("price"))],
      )).flatten(),
    )

    #v(0.6cm)

    #align(right)[
      #grid(
        columns: (4.5cm, 3cm),
        column-gutter: 0.5cm,
        [Subtotal], align(right)[#money(record.at("subtotal"))],
        [Tax], align(right)[#money(record.at("tax"))],
        grid.cell(stroke: (top: 0.5pt + gray))[#v(0.3em)],
        grid.cell(stroke: (top: 0.5pt + gray))[#v(0.3em)],
        text(weight: "bold", size: 12pt)[Total Due],
        text(weight: "bold", size: 12pt, fill: rgb("#1f3a5f"))[#money(record.at("total"))],
      )
    ]

    #v(1.2cm)
    #align(center, text(size: 9pt, fill: gray)[
      Payment due within 30 days. Thank you for your business!
    ])
  ]
}

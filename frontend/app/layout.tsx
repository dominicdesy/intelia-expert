export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="fr">
      <head>
        <title>Intelia Expert</title>
        <meta name="description" content="Assistant IA en santé et nutrition animale" />
      </head>
      <body>
        {children}
      </body>
    </html>
  )
}

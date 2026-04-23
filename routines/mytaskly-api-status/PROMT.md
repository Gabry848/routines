Usa l'MCP server chiamato notion per cercare il database "MyTaskly API Changes".
Se non lo trovi subito, cerca anche varianti come "MyTaskly — API Changes" o "API Changes".

Obiettivo:
1. Trova tutti gli elementi con stato "pending" nel database.
2. Trova tutti gli elementi con stato "in progress" (o "in_progress", "In Progress") nel database.
3. Scrivi i risultati in un file in /reports/ chiamato api_status_YYYY-MM-DD.md.

Struttura del file di output:
- **Titolo**: MyTaskly API Changes — Report del YYYY-MM-DD
- **Sezione "In Progress"**: elenca ogni elemento con nome, descrizione (se presente), data aggiornamento.
- **Sezione "Pending"**: elenca ogni elemento con nome, descrizione (se presente), data creazione.
- **Sommario**: conta totale in progress + totale pending.

Se il database non viene trovato, scrivi nel report i tentativi fatti e i possibili motivi.
Se non ci sono elementi in una delle due categorie, indica "Nessun elemento" per quella sezione.

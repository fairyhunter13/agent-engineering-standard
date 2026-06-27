---
name: sql-injection
description: Prevent SQL injection by using parameterized queries, ORM query builders, and DB least-privilege — and verify with sqlmap in your security pipeline.
discipline: security
tags: [security, sql-injection, owasp, parameterized-queries, database]
---

# SQL Injection

## When to use
Apply this skill when writing any code that constructs SQL queries; during code review of database interaction code; when a security scan or penetration test reports SQL injection findings; or when auditing legacy code that uses string concatenation for SQL.

## Signal
- SQL query built with string concatenation or f-strings:
  ```python
  query = f"SELECT * FROM users WHERE name = '{name}'"
  query = "SELECT * FROM orders WHERE id = " + order_id
  ```
- Dynamic `ORDER BY` or `LIMIT` column/values from user input without allowlisting.
- Raw SQL executed via `.raw()`, `cursor.execute()`, or `db.query()` with interpolated variables.
- `sqlmap` or `OWASP ZAP` reports an injection point.
- `LIKE '%' + user_input + '%'` pattern without parameterization.
- ORM `.raw()` or `.extra()` methods used with user-controlled values.

## Why
SQL injection has been in the OWASP Top 10 every year since 2003 and remains one of the most exploited vulnerability classes in 2025. A successful SQLi attack can: dump the entire database (SELECT), modify or delete records (UPDATE/DELETE), bypass authentication (OR '1'='1'), execute OS commands (via `xp_cmdshell` in SQL Server or `COPY TO/FROM` in Postgres with superuser), and read/write files on the server. It is trivially detectable and exploitable with automated tools like `sqlmap`. Despite being well-understood, it persists in codebases because string interpolation is convenient and developers underestimate the risk.

## Remediate

1. **Always use parameterized queries (prepared statements).** This is the primary, complete defense against SQL injection. Parameters are never interpreted as SQL syntax — they are always treated as data:
   ```python
   # Python — DB-API 2.0 (psycopg2, sqlite3, etc.)
   # Bad — injectable
   cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")

   # Good — parameterized
   cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
   # Or with named params
   cursor.execute("SELECT * FROM users WHERE email = %(email)s", {'email': email})
   ```
   ```ts
   // Node.js — pg (PostgreSQL)
   // Bad
   await client.query(`SELECT * FROM users WHERE email = '${email}'`);

   // Good
   await client.query('SELECT * FROM users WHERE email = $1', [email]);
   ```
   ```java
   // Java — JDBC PreparedStatement
   PreparedStatement stmt = conn.prepareStatement(
       "SELECT * FROM users WHERE email = ?"
   );
   stmt.setString(1, email);
   ResultSet rs = stmt.executeQuery();
   ```

2. **Use ORM query builders — not raw SQL.** ORMs build parameterized queries automatically:
   ```ts
   // Prisma (TypeScript) — safe by default
   const user = await prisma.user.findFirst({
     where: { email: email },  // parameterized automatically
   });

   // TypeORM — use query builder or repository methods, not .query()
   const user = await userRepo.findOne({ where: { email } });
   ```
   ```python
   # Django ORM — safe by default
   User.objects.filter(email=email)  # parameterized

   # SQLAlchemy — use ORM or Core with bound parameters
   session.query(User).filter(User.email == email)
   ```
   Never use `Model.objects.raw()` (Django), `.execute()` (SQLAlchemy text), or `.query()` (Prisma) with interpolated user input.

3. **Allowlist dynamic SQL fragments.** Some use cases require dynamic SQL structure (e.g., dynamic `ORDER BY` column, dynamic table selection). Never use user input directly — validate against a hardcoded allowlist:
   ```ts
   const ALLOWED_SORT_COLUMNS = ['created_at', 'price', 'name', 'updated_at'] as const;
   type SortColumn = typeof ALLOWED_SORT_COLUMNS[number];

   function buildOrderClause(column: string, direction: string): string {
     const safeColumn = ALLOWED_SORT_COLUMNS.includes(column as SortColumn)
       ? column
       : 'created_at';  // default
     const safeDirection = direction === 'desc' ? 'DESC' : 'ASC';
     return `ORDER BY ${safeColumn} ${safeDirection}`;  // safe — allowlisted
   }
   ```

4. **Apply database least privilege.** The application DB user should have only the permissions it needs:
   ```sql
   -- Create a role with minimum permissions
   CREATE ROLE app_user WITH LOGIN PASSWORD 'secure_password';
   GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
   -- DO NOT grant:
   -- GRANT DROP, TRUNCATE, CREATE ON ... (DDL permissions)
   -- GRANT SUPERUSER (never)
   -- Access to pg_catalog or system tables
   ```
   Even if SQLi occurs, a limited role prevents DROP TABLE, file access, and cross-database attacks.

5. **Use a stored procedure layer for sensitive operations.** For financial operations, consider stored procedures with strict parameter typing. The DB engine validates parameter types before execution, adding an additional injection barrier.

6. **Test for SQLi in your security pipeline.** Run `sqlmap` against your API in a non-production environment:
   ```sh
   # sqlmap automated scan against an authenticated API endpoint
   sqlmap -u "https://staging.example.com/api/users?id=1" \
     --cookie="session=abc123" \
     --level=5 --risk=3 \
     --batch \
     --output-dir=./sqlmap-results
   ```
   Add OWASP ZAP or Nuclei to your nightly DAST scan to detect injection points automatically.

7. **Add SAST rules for SQL injection patterns.** Catch injection patterns at code review time with static analysis:
   ```sh
   # semgrep rules for SQLi
   semgrep --config "p/sql-injection" .
   # Catches: string concatenation in SQL, f-string interpolation in query calls
   ```
   ```yaml
   # Custom semgrep rule example
   rules:
     - id: sql-injection-fstring
       pattern: cursor.execute(f"...{$VAR}...")
       message: "Possible SQL injection via f-string interpolation"
       severity: ERROR
   ```

## References
- OWASP A03:2021 – Injection (SQLi is the primary case)
- OWASP SQL Injection Prevention Cheat Sheet
- sqlmap (sqlmapproject/sqlmap) — automated SQL injection tool
- OWASP Testing Guide — Testing for SQL Injection (OTG-INPVAL-005)

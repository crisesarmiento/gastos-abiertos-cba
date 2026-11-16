"""CLI de gastos-abiertos-cba. Etapa 0: esqueleto; los comandos se implementan por etapa."""
import argparse, sys


def main(argv=None):
    p = argparse.ArgumentParser(prog="gastos-abiertos")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("inventory", help="listar ZIPs oficiales (Etapa 1)")

    dl = sub.add_parser("download-official", help="descargar ZIPs oficiales (Etapa 1)")
    dl.add_argument("--dry-run", action="store_true", help="listar sin descargar ZIPs")
    dl.add_argument("--limit", type=int, help="máximo de ZIPs a descargar")

    sub.add_parser("ingest-official", help="ingerir XLSX a Parquet/CSV/DuckDB (Etapa 1)")
    c = sub.add_parser("crawl-api", help="microdato vía API (Etapa 2, requiere ok)")
    c.add_argument("--ejercicio", type=int, required=True)
    c.add_argument("--jurisdiccion"); c.add_argument("--limit", type=int)
    c.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    if args.cmd == "inventory":
        from .inventory import inventory
        inv = inventory()
        print(f"zips locales: {len(inv['local'])}  en catalogo guardado: {len(inv['remote'])}  faltan: {len(inv['faltan_local'])}")
        for n in inv["local"]: print(" ", n)
        return 0

    if args.cmd == "download-official":
        from .download import download_official, DEFAULT_CATALOG_URL
        from .http import BlockedError
        try:
            result = download_official(
                DEFAULT_CATALOG_URL,
                dry_run=args.dry_run,
                limit=args.limit,
            )
        except BlockedError as exc:
            print(f"BLOQUEADO: {exc}", file=sys.stderr)
            return 3
        if args.dry_run:
            print(f"dry-run: faltarían {len(result)} ZIPs")
            for url, dest in result:
                print(f"  {url} -> {dest}")
        else:
            print(f"descargados: {len(result)}")
        return 0

    if args.cmd == "ingest-official":
        from .ingest import run
        db, res, ng, nr = run()
        bad = [r for r in res if not r["ok"]]
        print(f"gastos={ng} recursos={nr} db={db} checks={len(res)} fallidos={len(bad)}")
        for b in bad: print("DESVIO", b)
        return 1 if bad else 0

    print(f"{args.cmd}: no implementado todavía", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())

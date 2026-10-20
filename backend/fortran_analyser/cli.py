"""Console entry point. stdout is always reserved for machine-readable JSON."""

import argparse
import json
import sys
from pathlib import Path

from .project import analyse_project


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Analiza código Fortran y devuelve JSON.")
    parser.add_argument("path", type=Path, help="Archivo o directorio local")
    parser.add_argument("--output", "-o", type=Path, help="Guardar JSON UTF-8 en este archivo")
    parser.add_argument("--source-form", choices=["auto", "fixed", "free"], default="auto")
    parser.add_argument("--max-file-bytes", type=int, default=2_000_000)
    parser.add_argument("--max-files", type=int, default=500)
    parser.add_argument("--timeout", type=float, default=10, help="Segundos por archivo")
    args = parser.parse_args(argv)
    try:
        if args.output and args.path.is_file() and args.output.resolve() == args.path.resolve():
            raise ValueError("El archivo de salida no puede sobrescribir la fuente de entrada.")
        report = analyse_project(
            args.path,
            source_form=args.source_form,
            max_file_bytes=args.max_file_bytes,
            max_files=args.max_files,
            timeout=args.timeout,
        )
        output = json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n"
        if args.output:
            if args.output.is_file():
                base = args.path if args.path.is_dir() else args.path.parent
                if any(args.output.samefile(base / file.path) for file in report.files):
                    raise ValueError(
                        "El archivo de salida no puede sobrescribir una fuente analizada."
                    )
            args.output.write_text(output, encoding="utf-8")
        else:
            # Escaped non-ASCII JSON also works on Windows consoles using legacy encodings.
            print(json.dumps(report.to_dict(), ensure_ascii=True, indent=2))
        return 0 if all(f.status == "ok" for f in report.files) else 1
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

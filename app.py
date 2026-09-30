"""Dental Considerations: a Flask port of the Express + React drug lookup tool."""

from __future__ import annotations

import os

from flask import Flask, jsonify, render_template, request

from drugs import Drug, DrugStore

VERSION = "0.6.12"
MAX_DRUGS = 20
MAX_NAME_LEN = 100


def clean_names(values: list) -> list[str]:
    """Trim, drop blanks, and cap to the same limits the original zod schema enforced."""
    names = [v.strip() for v in values if isinstance(v, str) and v.strip()]
    return [n[:MAX_NAME_LEN] for n in names][:MAX_DRUGS]


def results_as_text(results: list[tuple[str, Drug | None]]) -> str:
    """Plain-text summary for the "Copy Results" button (same format as the React app)."""
    lines: list[str] = []
    for query, drug in results:
        if drug is None:
            lines.append(f"{query}\n  Not found in database.")
        else:
            lines.append(drug.generic_name or drug.name)
            lines.append(f"  Class: {drug.drug_class or 'N/A'}")
            if drug.side_effects:
                lines.append("  Side Effects:")
                lines.extend(f"    • {s.effect}" for s in drug.side_effects)
        lines.append("")
    return "\n".join(lines).strip()


def create_app(store: DrugStore | None = None) -> Flask:
    app = Flask(__name__)
    store = store or DrugStore.from_json()
    app.config["DRUG_STORE"] = store

    @app.context_processor
    def inject_globals():
        return {"version": VERSION, "max_drugs": MAX_DRUGS}

    # ── Pages ────────────────────────────────────────────────────────────────

    @app.get("/")
    def index():
        # Searches are plain GET params (/?drug=Lexapro&drug=Warfarin), so a
        # result page can be bookmarked, shared, or reloaded.
        queries = clean_names(request.args.getlist("drug"))
        results = list(zip(queries, store.search(queries)))
        found = sum(1 for _, d in results if d)
        return render_template(
            "index.html",
            drugs=store.drugs,
            common_uses=store.common_uses(),
            inputs=queries or ["", ""],
            results=results,
            found_count=found,
            not_found_count=len(results) - found,
            copy_text=results_as_text(results),
        )

    @app.get("/changelog")
    def changelog():
        return render_template("changelog.html")

    # ── JSON API (same shape as the Express routes) ──────────────────────────

    @app.post("/api/drugs/search")
    def api_search():
        body = request.get_json(silent=True) or {}
        names = body.get("names")
        if (
            not isinstance(names, list)
            or not 1 <= len(names) <= MAX_DRUGS
            or not all(isinstance(n, str) and 1 <= len(n) <= MAX_NAME_LEN for n in names)
        ):
            return jsonify(error="Invalid request"), 400
        return jsonify(
            results=[d.to_dict() if d else None for d in store.search(names)]
        )

    @app.get("/api/drugs")
    def api_drugs():
        return jsonify(
            drugs=[
                {"id": d.id, "name": d.name, "genericName": d.generic_name, "drugClass": d.drug_class}
                for d in store.drugs
            ]
        )

    @app.get("/api/drugs/names")
    def api_names():
        return jsonify(
            drugs=[
                {"name": d.name, "genericName": d.generic_name, "commonUse": d.common_use}
                for d in store.drugs
            ]
        )

    @app.get("/api/drugs/autocomplete")
    def api_autocomplete():
        matches = store.autocomplete(request.args.get("q", ""))
        return jsonify(
            suggestions=[{"name": d.name, "genericName": d.generic_name} for d in matches]
        )

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("not_found.html"), 404

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)

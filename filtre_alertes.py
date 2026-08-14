#!/usr/bin/env python3
"""
Filtre un export CSV d'alertes pharmaceutiques AVICENNE.

Par défaut, ne conserve que les lignes dont l'identifiant de règle
est « A1 » (alertes « Antibiotiques prescrits depuis 2 à 4 jours à
réévaluer »). Le filtre est paramétrable en ligne de commande.

Usage
-----
    python3 filtre_alertes.py entree.csv                       # -> entree_A1.csv
    python3 filtre_alertes.py entree.csv -o sortie.csv
    python3 filtre_alertes.py entree.csv -c "Identifiant règle=A1"
    python3 filtre_alertes.py entree.csv -c "UF=USC" -c "Criticité de la règle=0"

Un fichier `-` pour l'entrée ou la sortie utilise l'entrée/sortie standard.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


def nettoyer_colonnes(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise les noms de colonnes : retire les espaces de fin."""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def parse_condition(condition: str) -> tuple[str, str]:
    """Sépare une condition 'Nom colonne=valeur' en (colonne, valeur)."""
    if "=" not in condition:
        raise argparse.ArgumentTypeError(
            f"Condition invalide '{condition}' : attendu 'Nom colonne=valeur'"
        )
    colonne, valeur = condition.split("=", 1)
    return colonne.strip(), valeur


def appliquer_filtre(df: pd.DataFrame, colonne: str, valeur: str) -> pd.DataFrame:
    """Filtre df en gardant les lignes où `colonne` == `valeur`.

    Comparaison insensible à la casse et aux espaces, tolérante aux
    valeurs manquantes (jamais égales à un filtre non vide).
    """
    if colonne not in df.columns:
        colonnes_dispo = ", ".join(repr(c) for c in df.columns)
        raise SystemExit(
            f"Colonne '{colonne}' introuvable. Colonnes disponibles : {colonnes_dispo}"
        )
    serie = df[colonne].astype(str).str.strip().str.casefold()
    return df[serie == valeur.strip().casefold()]


def filtrer_a1(df: pd.DataFrame) -> pd.DataFrame:
    """Raccourci : ne conserver que les alertes de règle A1."""
    return appliquer_filtre(df, "Identifiant règle", "A1")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Filtre un export CSV d'alertes pharmaceutiques AVICENNE.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("entree", help="Fichier CSV d'entrée ('-' = stdin)")
    parser.add_argument(
        "-o", "--sortie",
        help="Fichier CSV de sortie ('-' = stdout). Défaut : <entree>_A1.csv",
    )
    parser.add_argument(
        "-c", "--condition",
        action="append", default=[], type=parse_condition,
        metavar="'COLONNE=VALEUR'",
        help="Filtre supplémentaire (cumulable). Ex : -c 'UF=USC'. "
             "Sans -c, filtre par défaut Identifiant règle=A1.",
    )
    parser.add_argument(
        "-d", "--delimiter", default="\t",
        help="Séparateur du CSV (défaut : tabulation)",
    )
    args = parser.parse_args(argv)

    entree = args.entree
    if args.sortie is None:
        base = "stdin" if entree == "-" else entree
        sortie = f"{Path(base).stem}_A1.csv"
    else:
        sortie = args.sortie

    source = sys.stdin if entree == "-" else entree
    try:
        df = pd.read_csv(source, sep=args.delimiter, dtype=str, keep_default_na=False)
    except FileNotFoundError:
        raise SystemExit(f"Fichier introuvable : {entree}")
    except pd.errors.EmptyDataError:
        raise SystemExit(f"Fichier vide : {entree}")

    df = nettoyer_colonnes(df)
    n_initial = len(df)

    conditions = args.condition or [("Identifiant règle", "A1")]
    for colonne, valeur in conditions:
        df = appliquer_filtre(df, colonne, valeur)

    n_final = len(df)
    print(
        f"{n_initial} lignes -> {n_final} lignes après filtrage "
        f"({n_initial - n_final} retirées)",
        file=sys.stderr,
    )

    cible = sys.stdout if sortie == "-" else sortie
    df.to_csv(cible, sep=args.delimiter, index=False)
    if sortie != "-":
        print(f"Résultat écrit dans : {sortie}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

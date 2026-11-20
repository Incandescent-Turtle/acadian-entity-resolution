"""Petites familles construites à la main (aucune base, aucun code du projet)."""

import pytest

from familles import personne, relier


@pytest.fixture
def famille():
    """Jean Babin + Marie Léger -> Pierre, Anne ; Pierre + Cécile -> Joseph."""
    jean = personne("I1", "Jean Babin", "M", 1700, nom_famille="Babin")
    marie = personne("I2", "Marie Léger", "F", 1705, nom_famille="Léger")
    pierre = personne("I3", "Pierre Babin", "M", 1726, nom_famille="Babin")
    anne = personne("I4", "Anne Babin", "F", 1728, nom_famille="Babin")
    cecile = personne("I5", "Cécile Comeau", "F", 1730, nom_famille="Comeau")
    joseph = personne("I6", "Joseph Babin", "M", 1752, nom_famille="Babin")
    relier(jean, marie, [pierre, anne])
    relier(pierre, cecile, [joseph])
    return [jean, marie, pierre, anne, cecile, joseph]

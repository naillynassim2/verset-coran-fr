#!/usr/bin/env python3
"""
Bot Barre de Progression FR
----------------------------
Poste sur X (Twitter) une image montrant le pourcentage de l'année
écoulée, accompagnée d'un texte en français. Conçu pour être lancé
périodiquement (ex: via un cron ou GitHub Actions).
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import tweepy
from PIL import Image, ImageDraw, ImageFont

ETAT_FICHIER = Path(__file__).parent / "etat.json"
LARGEUR_IMG = 1200
HAUTEUR_IMG = 400

COULEUR_FOND = (255, 255, 255)
COULEUR_BARRE = (0, 85, 184)
COULEUR_TEXTE = (20, 20, 20)
COULEUR_SOUS_TEXTE = (120, 120, 120)


def calculer_pourcentage_annee(maintenant: datetime):
    """Retourne (annee, pourcentage_entier_de_0_a_100)."""
    annee = maintenant.year
    debut_annee = datetime(annee, 1, 1, tzinfo=timezone.utc)
    debut_annee_suivante = datetime(annee + 1, 1, 1, tzinfo=timezone.utc)
    duree_totale = (debut_annee_suivante - debut_annee).total_seconds()
    duree_ecoulee = (maintenant - debut_annee).total_seconds()
    pourcentage = int((duree_ecoulee / duree_totale) * 100)
    return annee, min(pourcentage, 100)


def lire_etat() -> dict:
    if ETAT_FICHIER.exists():
        return json.loads(ETAT_FICHIER.read_text())
    return {"annee": None, "dernier_pourcentage": -1}


def ecrire_etat(annee: int, pourcentage: int) -> None:
    ETAT_FICHIER.write_text(json.dumps({"annee": annee, "dernier_pourcentage": pourcentage}))


def generer_image(annee: int, pourcentage: int, chemin_sortie: str) -> None:
    img = Image.new("RGB", (LARGEUR_IMG, HAUTEUR_IMG), (0, 0, 0))  # fond noir
    draw = ImageDraw.Draw(img)

    marge_x = 90
    marge_y = 180
    hauteur_barre = 110
    largeur_barre = LARGEUR_IMG - 2 * marge_x
    rayon = hauteur_barre // 2

    # Bordure blanche en forme de pilule
    draw.rounded_rectangle(
        [marge_x, marge_y, marge_x + largeur_barre, marge_y + hauteur_barre],
        radius=rayon, fill=(255, 255, 255),
    )
    # Piste noire à l'intérieur
    inset1 = 10
    draw.rounded_rectangle(
        [marge_x + inset1, marge_y + inset1, marge_x + largeur_barre - inset1, marge_y + hauteur_barre - inset1],
        radius=rayon - inset1, fill=(0, 0, 0),
    )
    # Remplissage vert proportionnel
    inset2 = 18
    largeur_dispo = largeur_barre - 2 * inset2
    largeur_remplie = int(largeur_dispo * (pourcentage / 100))
    if largeur_remplie > 0:
        draw.rounded_rectangle(
            [marge_x + inset2, marge_y + inset2, marge_x + inset2 + largeur_remplie, marge_y + hauteur_barre - inset2],
            radius=max(rayon - inset2, 4), fill=(0, 230, 80),
        )

    try:
        police_titre = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52
        )
    except OSError:
        police_titre = ImageFont.load_default()

    texte_titre = f"{annee} est complétée à {pourcentage} %."
    bbox = draw.textbbox((0, 0), texte_titre, font=police_titre)
    largeur_texte = bbox[2] - bbox[0]
    draw.text(
        ((LARGEUR_IMG - largeur_texte) / 2, 65),
        texte_titre,
        font=police_titre,
        fill=(255, 255, 255),
    )

    img.save(chemin_sortie)


def poster_sur_x(texte: str, chemin_image: str) -> None:
    api_key = os.environ["X_API_KEY"]
    api_secret = os.environ["X_API_SECRET"]
    access_token = os.environ["X_ACCESS_TOKEN"]
    access_secret = os.environ["X_ACCESS_SECRET"]

    # L'upload de média nécessite encore l'authentification OAuth1 (API v1.1)
    auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
    api_v1 = tweepy.API(auth)
    media = api_v1.media_upload(chemin_image)

    # La création du tweet se fait via l'API v2
    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_secret,
    )
    client.create_tweet(text=texte, media_ids=[media.media_id])


def main() -> None:
    maintenant = datetime.now(timezone.utc)
    annee, pourcentage = calculer_pourcentage_annee(maintenant)

    etat = lire_etat()
    if etat["annee"] == annee and etat["dernier_pourcentage"] >= pourcentage:
        print(f"Rien à faire : {annee} est déjà annoncée à {etat['dernier_pourcentage']} %.")
        return

    chemin_image = "/tmp/barre_progression.png"
    generer_image(annee, pourcentage, chemin_image)

    texte = f"L'année {annee} est complétée à {pourcentage} %."
    poster_sur_x(texte, chemin_image)
    ecrire_etat(annee, pourcentage)
    print(f"Tweet envoyé : {texte}")


if __name__ == "__main__":
    main()

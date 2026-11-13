---
name: psani-pruvodce
description: >-
  Writes and edits public project guides and READMEs for a stranger, not as
  notes for the people building the project. Use when creating or changing a
  guide, průvodce, README, onboarding text, or when the user mentions text
  formatting or writing rules for a guide.
---

# Psaní průvodce

Platí pro veřejný text o projektu: průvodce, README, úvod pro nového čtenáře. Piš v jazyce, který ten dokument už používá.

Čtenář projekt nezná. Po přečtení ho má umět popsat vlastními slovy.

Když uživatel text přepíše ručně, jeho znění nech. Nevracej věty, které smazal, a nezkrášluj jeho formulace.

## Co v textu zůstává

- Co věc dělá pro člověka, který ji vidí poprvé. Ne proč ji tým vyrobil. „Okno, které simuluje vstupy“ ano. „Zkouška, jestli nám to naběhne“ ne.
- Jak se to spustí: kliknutí, které opravdu funguje, a příkaz, který udělá totéž.
- Krátký komentář přímo nad řádkem, který vysvětluje. Stejnou větu už neopakuj pod ukázkou kódu.

## Co se maže

- Poznámky jen pro výrobce: interní postup, staré pokusy, co se bude dělat později, proč editor něco nespustí, „až přibude další krok, dopíšeme to sem“.
- Dovětek, který jen rozepisuje údaj, který na řádku už je.

## Před a po

Před:

```python
# Rozměr okna v pixelech, tedy v bodech na obrazovce.
# 960x600 znamená 960 bodů na šířku a 600 na výšku.
# Písmeno x uprostřed je součást zápisu, není to krát.
SIZE = "960x600"
```

Po:

```python
# Rozměr okna v pixelech.
# Písmeno x je součást zápisu.
SIZE = "960x600"
```

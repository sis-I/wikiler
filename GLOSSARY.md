# Glossary

## vault

A bounded collection of source material and the knowledge pages derived from
it, together with the catalog and timeline that track those pages.

## page

A unit of knowledge in a vault that records claims, definitions, or synthesis
and links to related pages.

## raw source

An immutable input document supplied by a human, from which knowledge pages
are derived.

## source page

A page derived from one raw source, recording that source's metadata, summary,
and key claims.

## entity

A page about a distinct thing, such as a person, organization, system, or
project.

## concept

A page about an idea, method, or principle that can recur across sources.

## synthesis

A page that combines material from several pages into a new answer,
comparison, or analysis.

## query

A page that records a question asked of the vault and the pages considered
while answering it.

## wikilink

A cross-reference from one page to another page in the vault.

## index

The catalog that lists every page in a vault, grouped by kind.

## log

The append-only timeline that records operations performed on a vault.

## asset

A non-text resource, such as an image, referenced by a source or a page and
kept alongside the source material.

## normative

The canonical source for a topic. A normative document wins conflicts with
non-normative documents, changes only through an explicit recorded decision,
and is linked to rather than restated by other documents.

## corrected guide

A normative guide whose claims have been checked against the shipped engine
and the locked decisions, and clarified editorially where the source material
was ambiguous.

## third-party claim

A statement about an external project or person that is not a statement about
Wikiler behavior.

## caveat

A qualification attached to a third-party claim. It records attribution, a
source URL, and an access date, and states that the claim is illustrative only,
not Wikiler behavior. A numeric claim also states that the source reports the
figure and that it was not independently verified.

## status marker

A `Status: <value>` line in a public document that records the document's
authority status in a form a mechanical check can find without reading prose.

import { toCents } from "../utils/amount";
import type { Row } from "./types";

type AddChange = {
  op: "add";
  date: string;
  accnum: string;
  acclib: string;
  lib: string;
  debit: number;
  credit: number;
};

type ModifyChange = {
  op: "modify";
  entry_id: number;
  date: string;
  accnum: string;
  acclib: string;
  lib: string;
  debit: number;
  credit: number;
};

type DeleteChange = {
  op: "delete";
  entry_id: number;
};

export type Change = AddChange | ModifyChange | DeleteChange;

/**
 * Construit la liste des changements en comparant l'état initial et l'état courant.
 * - Lignes avec id manquant -> add
 * - Lignes initiales marquées deleted -> delete
 * - Lignes initiales modifiées -> modify
 */
export function diffChanges(initial: Row[], current: Row[]): Change[] {
  const byIdInitial = new Map<number, Row>();
  for (const r of initial) if (r.id != null) byIdInitial.set(r.id, r);

  const changes: Change[] = [];

  // ADD + MODIFY + DELETE
  for (const curr of current) {
    if (curr.markedDeleted) continue; // delete sera traité par initial
    if (curr.id == null) {
      // new row -> add
      changes.push({
        op: "add",
        date: curr.date,
        accnum: curr.accnum,
        acclib: curr.acclib, // utilisé seulement si on crée le compte
        lib: curr.lib,
        debit: toCents(curr.debit),
        credit: toCents(curr.credit),
      });
      continue;
    }

    // existing -> compare with initial
    const init = byIdInitial.get(curr.id);
    if (!init) {
      // sécurité: si pas trouvé, considère comme add (ou ignore)
      changes.push({
        op: "add",
        date: curr.date,
        accnum: curr.accnum,
        acclib: curr.acclib,
        lib: curr.lib,
        debit: toCents(curr.debit),
        credit: toCents(curr.credit),
      });
      continue;
    }

    if (isRowModified(init, curr)) {
      changes.push({
        op: "modify",
        entry_id: curr.id!,
        date: curr.date,
        accnum: curr.accnum,
        acclib: curr.acclib, // ignoré si le compte existe déjà côté serveur
        lib: curr.lib,
        debit: toCents(curr.debit),
        credit: toCents(curr.credit),
      });
    }
  }

  // deletions: lignes présentes au départ mais absentes maintenant OU flaggées deleted
  const currentById = new Map<number, Row>();
  for (const r of current) if (r.id != null) currentById.set(r.id, r);

  for (const init of initial) {
    if (init.id == null) continue;
    const curr = currentById.get(init.id);
    if (!curr) {
      // supprimée (p. ex. via filtrage "isNew" faux-positif)
      changes.push({ op: "delete", entry_id: init.id });
    } else if (curr.markedDeleted) {
      changes.push({ op: "delete", entry_id: init.id });
    }
  }

  return changes;
}

function isRowModified(a: Row, b: Row): boolean {
  return (
    a.date !== b.date ||
    (a.accnum || "") !== (b.accnum || "") ||
    (a.acclib || "") !== (b.acclib || "") ||
    (a.lib || "") !== (b.lib || "") ||
    toCents(a.debit || "") !== toCents(b.debit || "") ||
    toCents(a.credit || "") !== toCents(b.credit || "")
  );
}

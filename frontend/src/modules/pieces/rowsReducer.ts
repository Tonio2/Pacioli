// src/modules/pieces/rowsReducer.ts
import type { Row, RowBase } from "./types";

export const makeRow = (partial?: Partial<Row>): Row => ({
  uid: crypto.randomUUID(),
  date: new Date().toISOString().slice(0, 10),
  accnum: "",
  acclib: "",
  lib: "",
  debit: "",
  credit: "",
  _accountExists: false,
  ...partial,
});

export type RowAction =
  | { type: "set"; rows: Row[] }
  | { type: "add"; row?: Partial<RowBase> }
  | { type: "update"; uid: string; patch: Partial<Row> }
  | { type: "delete"; uid: string; isNew?: boolean } // isNew -> supprime vraiment; sinon flagged
  | { type: "undoDelete"; uid: string };

export function rowsReducer(state: Row[], action: RowAction): Row[] {
  switch (action.type) {
    case "set":
      return action.rows;

    case "add":
      return [...state, makeRow(action.row)];

    case "update":
      return state.map((r) => (r.uid === action.uid ? { ...r, ...action.patch } : r));

    case "delete": {
      const row = state.find((r) => r.uid === action.uid);
      if (!row) return state;
      // si la ligne n'existe pas en base (pas d'id), on la retire vraiment
      if (action.isNew || !row.id) {
        return state.filter((r) => r.uid !== action.uid);
      }
      // sinon, flag visual
      return state.map((r) => (r.uid === action.uid ? { ...r, markedDeleted: true } : r));
    }

    case "undoDelete":
      return state.map((r) => (r.uid === action.uid ? { ...r, markedDeleted: false } : r));

    default:
      return state;
  }
}

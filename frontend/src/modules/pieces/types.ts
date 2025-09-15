export type SuggestItem = { account_id: number; accnum: string; acclib: string };

export type RowBase = {
  id?: number;
  date: string;
  jnl?: string;
  piece_ref?: string;
  accnum: string;
  acclib: string;
  lib: string;
  debit: string;  // string saisi par l'utilisateur
  credit: string; // string saisi par l'utilisateur
};

export type Row = RowBase & {
  uid: string;                     // clé stable côté UI
  _accountExists?: boolean;        // pour désactiver libellé compte si existe
  markedDeleted?: boolean;         // flag UI pour suppression (ligne existante)
};

export type TotalsInfo = {
  debit: number;
  credit: number;
  diff: number;
  isBalanced: boolean;
  hasAmountErrors: boolean;
  bothSidesFilled: boolean; // les deux montants sur une même ligne
};

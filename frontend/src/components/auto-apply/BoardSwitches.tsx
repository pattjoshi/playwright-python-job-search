import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import type { AutoApplyOverview, AutoApplySettings, BoardId } from "@/lib/types";

import { BOARD_NAMES } from "./meta";

interface BoardSwitchesProps {
  form: AutoApplySettings;
  boards: AutoApplyOverview["boards"];
  onChange: (form: AutoApplySettings) => void;
}

/** Easy Apply on each job board: off until you turn it on, and only with that board's login in .env. */
export function BoardSwitches({ form, boards, onChange }: BoardSwitchesProps) {
  const toggle = (board: BoardId, on: boolean) =>
    onChange({ ...form, [board]: on, show_browser: on ? true : form.show_browser }); // watch it, solve OTPs and checks
  return (
    <div className="grid grid-cols-1 gap-3 border-t pt-4">
      <div>
        <p className="text-sm font-medium">Job boards (Easy Apply)</p>
        <p className="text-xs text-muted-foreground">
          Applies on the board itself with your login. Slow and careful, but boards may still restrict accounts that apply automatically.
        </p>
      </div>
      {(Object.keys(BOARD_NAMES) as BoardId[]).map((board) => {
        const info = boards[board];
        return (
          <label key={board} className="flex items-start gap-3">
            <Switch
              checked={form[board]} disabled={!info.has_login && !form[board]} onCheckedChange={(on) => toggle(board, on)}
              aria-label={`${BOARD_NAMES[board]} Easy Apply`} className="mt-0.5"
            />
            <span className="grid gap-0.5">
              <span className="text-sm font-medium">{BOARD_NAMES[board]}</span>
              <span className="text-xs text-muted-foreground">
                {info.has_login
                  ? `${info.today} of ${form.board_daily_limit} today`
                  : `Add ${board.toUpperCase()}_EMAIL and ${board.toUpperCase()}_PASSWORD to .env, then restart`}
              </span>
            </span>
          </label>
        );
      })}
      <label className="grid gap-1.5 text-sm font-medium">
        Applications per board per day
        <Input
          type="number" min={1} max={50} value={form.board_daily_limit}
          onChange={(e) => onChange({ ...form, board_daily_limit: Number.parseInt(e.target.value, 10) || 0 })}
        />
      </label>
    </div>
  );
}

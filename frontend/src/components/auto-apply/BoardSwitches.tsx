import { LogIn } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import type { AutoApplyOverview, AutoApplySettings, BoardId } from "@/lib/types";

import { BOARD_NAMES } from "./meta";

interface BoardSwitchesProps {
  form: AutoApplySettings;
  boards: AutoApplyOverview["boards"];
  onChange: (form: AutoApplySettings) => void;
  onSignIn: (board: BoardId) => void;
  busy: boolean;
}

function status(info: AutoApplyOverview["boards"][BoardId]): string {
  if (info.signed_in) return "Signed in";
  if (info.has_login) return "Login saved in .env";
  return "Not signed in yet: press Sign in";
}

/** Easy Apply on each job board: off until you turn it on. Sign in once in the app's browser (or keep a login in .env). */
export function BoardSwitches({ form, boards, onChange, onSignIn, busy }: BoardSwitchesProps) {
  const toggle = (board: BoardId, on: boolean) =>
    onChange({ ...form, [board]: on, show_browser: on ? true : form.show_browser }); // watch it, solve OTPs and checks
  return (
    <div className="grid grid-cols-1 gap-3 border-t pt-4">
      <div>
        <p className="text-sm font-medium">Job boards (Easy Apply)</p>
        <p className="text-xs text-muted-foreground">
          Applies on the board itself with your account. Press Sign in and log in once in the window that opens (OTP included); it
          stays signed in. Slow and careful, but boards may still restrict accounts that apply automatically.
        </p>
      </div>
      {(Object.keys(BOARD_NAMES) as BoardId[]).map((board) => {
        const info = boards[board];
        return (
          <div key={board} className="flex items-start gap-3">
            <Switch
              checked={form[board]} onCheckedChange={(on) => toggle(board, on)} aria-label={`${BOARD_NAMES[board]} Easy Apply`}
              className="mt-0.5"
            />
            <span className="grid min-w-0 flex-1 gap-0.5">
              <span className="text-sm font-medium">{BOARD_NAMES[board]}</span>
              <span className="text-xs text-muted-foreground">{status(info)} · {info.today} of {form.board_daily_limit} today</span>
            </span>
            <Button variant="outline" size="sm" disabled={busy} onClick={() => onSignIn(board)} aria-label={`Sign in to ${BOARD_NAMES[board]}`}>
              <LogIn /> {info.signed_in ? "Sign in again" : "Sign in"}
            </Button>
          </div>
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

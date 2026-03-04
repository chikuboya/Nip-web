from pyscript import window, document
from pyodide.ffi import create_proxy
import math
import random
import time

# --- 盤面定義 (Kivy版と完全一致) ---
VALID_COORDS = [(2,0), (3,0), (4,0), (5,0), (2,7), (3,7), (4,7), (5,7), (1,1), (2,1), (3,1), (4,1), (5,1), (6,1), (1,6), (2,6), (3,6), (4,6), (5,6), (6,6), (0,2), (1,2), (2,2), (3,2), (4,2), (5,2), (6,2), (7,2), (0,3), (1,3), (2,3), (3,3), (4,3), (5,3), (6,3), (7,3), (0,4), (1,4), (2,4), (3,4), (4,4), (5,4), (6,4), (7,4), (0,5), (1,5), (2,5), (3,5), (4,5), (5,5), (6,5), (7,5)]
CIRCUMFERENCE = [(0,3), (0,2), (1,1), (2,0), (3,0), (4,0), (5,0), (6,1), (7,2), (7,3), (7,4), (7,5), (6,6), (5,7), (4,7), (3,7), (2,7), (1,6), (0,5), (0,4)]
STRATEGIC_NODES = [(0,3), (7,3), (3,0), (3,7), (0,2), (7,2), (0,5), (7,5)]

class NipWebGame:
    def __init__(self):
        self.canvas = document.getElementById("game-board")
        self.ctx = self.canvas.getContext("2d")
        self.status_label = document.getElementById("status-label")
        self.result_label = document.getElementById("result-label")
        
        # 描画パラメータ
        self.margin = 60
        self.cell_size = 62
        self.offset = 80

        # 初期状態
        self.mode = "PvP"
        self.cpu_color = "white"
        self.level = 5
        self.reset_game()
        self.setup_ui_events()

    def reset_game(self):
        self.board = {coord: None for coord in VALID_COORDS}
        self.board[(3,3)], self.board[(4,4)] = 'white', 'white'
        self.board[(4,3)], self.board[(3,4)] = 'black', 'black'
        self.turn = 'black'
        self.history = []
        self.last_move = None
        self.is_game_over = False
        self.pass_msg = ""
        self.result_label.style.display = "none"
        self.draw()
        if self.mode == "PvE" and self.cpu_color == "black":
            window.setTimeout(create_proxy(self.cpu_move), 1000)

    def draw(self):
        self.ctx.clearRect(0, 0, 600, 650)
        
        # 1. 格子線の描画 (Kivy版のLineロジック)
        self.ctx.strokeStyle = "black"
        self.ctx.lineWidth = 1.2
        for c in VALID_COORDS:
            x1 = self.offset + c[0] * self.cell_size
            y1 = self.offset + c[1] * self.cell_size
            for dx, dy in [(1,0), (0,1), (1,1), (1,-1)]:
                target = (c[0]+dx, c[1]+dy)
                if target in VALID_COORDS:
                    x2 = self.offset + target[0] * self.cell_size
                    y2 = self.offset + target[1] * self.cell_size
                    self.ctx.beginPath()
                    self.ctx.moveTo(x1, y1)
                    self.ctx.lineTo(x2, y2)
                    self.ctx.stroke()

        # 2. 外周の円の描画 (Kivy版のcircle)
        cx, cy = self.offset + 3.5 * self.cell_size, self.offset + 3.5 * self.cell_size
        self.ctx.beginPath()
        self.ctx.arc(cx, cy, self.cell_size * 3.8, 0, math.pi*2)
        self.ctx.lineWidth = 2
        self.ctx.stroke()

        # 3. 石とガイドの描画
        for coord in VALID_COORDS:
            x = self.offset + coord[0] * self.cell_size
            y = self.offset + coord[1] * self.cell_size
            stone = self.board[coord]
            
            if stone:
                # 石の影/枠
                self.ctx.beginPath()
                self.ctx.arc(x, y, self.cell_size*0.38, 0, math.pi*2)
                self.ctx.fillStyle = "black" if stone == 'black' else "white"
                self.ctx.fill()
                self.ctx.strokeStyle = "#888"
                self.ctx.lineWidth = 1
                self.ctx.stroke()
                
                # 最後に置いた石を赤枠でハイライト
                if coord == self.last_move:
                    self.ctx.beginPath()
                    self.ctx.arc(x, y, self.cell_size*0.4, 0, math.pi*2)
                    self.ctx.strokeStyle = "red"
                    self.ctx.lineWidth = 3
                    self.ctx.stroke()
            else:
                # 交点のドット (Kivy版の小さなEllipse)
                self.ctx.beginPath()
                self.ctx.arc(x, y, 4, 0, math.pi*2)
                self.ctx.fillStyle = "#556B2F"
                self.ctx.fill()
                
                # 置ける場所のガイド
                if not self.is_game_over and (self.mode=="PvP" or self.turn!=self.cpu_color):
                    if self.get_flipped(coord, self.turn, self.board):
                        self.ctx.beginPath()
                        self.ctx.arc(x, y, self.cell_size*0.2, 0, math.pi*2)
                        self.ctx.fillStyle = "rgba(255, 255, 204, 0.6)"
                        self.ctx.fill()

        self.update_status_ui()

    def update_status_ui(self):
        b = list(self.board.values()).count('black')
        w = list(self.board.values()).count('white')
        t_name = "黒" if self.turn == 'black' else "白"
        status = f"黒: {b}  白: {w} | 次: {t_name}"
        if self.pass_msg: status = f"{self.pass_msg} {status}"
        self.status_label.innerText = status

    # --- ロジック部分 (Kivy版から完全移植) ---
    def get_flipped(self, start, color, board_state):
        if board_state[start] is not None: return []
        opp = 'white' if color == 'black' else 'black'
        flipped = []
        # 通常方向
        for dx, dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
            path, curr = [], (start[0]+dx, start[1]+dy)
            while curr in VALID_COORDS:
                st = board_state.get(curr)
                if st == opp: path.append(curr)
                elif st == color:
                    if path: flipped.extend(path)
                    break
                else: break
                curr = (curr[0]+dx, curr[1]+dy)
        # 円周方向
        if start in CIRCUMFERENCE:
            idx = CIRCUMFERENCE.index(start)
            for d in [1, -1]:
                path = []
                for i in range(1, len(CIRCUMFERENCE)):
                    curr = CIRCUMFERENCE[(idx + i * d) % len(CIRCUMFERENCE)]
                    st = board_state[curr]
                    if st == opp: path.append(curr)
                    elif st == color:
                        if path: flipped.extend(path)
                        break
                    else: break
        return list(set(flipped))

    def evaluate_board(self, board, color):
        opp = 'white' if color == 'black' else 'black'
        score = 0
        filled = sum(1 for v in board.values() if v is not None)
        is_endgame = filled > 42
        for coord, st in board.items():
            if st is None: continue
            val = 1.0
            if coord in STRATEGIC_NODES: val += 25.0 if not is_endgame else 5.0
            elif coord in CIRCUMFERENCE: val += 10.0 if not is_endgame else 3.0
            if st == color: score += val
            else: score -= val
        return score

    def minimax(self, board, depth, alpha, beta, is_maximizing, color):
        if depth == 0: return self.evaluate_board(board, color)
        opp = 'white' if color == 'black' else 'black'
        curr_p = color if is_maximizing else opp
        moves = []
        for n in VALID_COORDS:
            f = self.get_flipped(n, curr_p, board)
            if f: moves.append((n, f))
        if not moves: return self.evaluate_board(board, color)
        
        if is_maximizing:
            v = -99999
            for m, f in moves:
                nb = board.copy()
                nb[m] = color
                for s in f: nb[s] = color
                v = max(v, self.minimax(nb, depth-1, alpha, beta, False, color))
                alpha = max(alpha, v)
                if beta <= alpha: break
            return v
        else:
            v = 99999
            for m, f in moves:
                nb = board.copy()
                nb[m] = opp
                for s in f: nb[s] = opp
                v = min(v, self.minimax(nb, depth-1, alpha, beta, True, color))
                beta = min(beta, v)
                if beta <= alpha: break
            return v

    def cpu_move(self):
        if self.is_game_over: return
        moves = [(n, self.get_flipped(n, self.turn, self.board)) for n in VALID_COORDS if self.get_flipped(n, self.turn, self.board)]
        if not moves: return

        # 難易度設定 (Kivy版のlv_cfg)
        lv_cfg = {
            1: {'d': 0, 'r': 0.7}, 2: {'d': 1, 'r': 0.5}, 3: {'d': 1, 'r': 0.3},
            4: {'d': 2, 'r': 0.2}, 5: {'d': 2, 'r': 0.1}, 6: {'d': 3, 'r': 0.05},
            7: {'d': 4, 'r': 0.0}, 8: {'d': 5, 'r': 0.0}, 9: {'d': 6, 'r': 0.0}, 10: {'d': 8, 'r': 0.0}
        }
        cfg = lv_cfg.get(self.level, lv_cfg[5])

        if random.random() < cfg['r']:
            self.make_move(random.choice(moves)[0])
        else:
            best_m, best_v = moves[0][0], -100000
            for m, f in moves:
                nb = self.board.copy()
                nb[m] = self.turn
                for s in f: nb[s] = self.turn
                val = self.minimax(nb, cfg['d'], -100000, 100000, False, self.turn)
                if val > best_v:
                    best_v, best_m = val, m
            self.make_move(best_m)

    def make_move(self, coord):
        to_flip = self.get_flipped(coord, self.turn, self.board)
        if to_flip:
            self.pass_msg = ""
            self.history.append({'board': self.board.copy(), 'turn': self.turn, 'last_move': self.last_move})
            self.board[coord] = self.turn
            self.last_move = coord
            for n in to_flip: self.board[n] = self.turn
            self.turn = 'white' if self.turn == 'black' else 'black'
            self.draw()
            window.setTimeout(create_proxy(self.check_pass), 300)

    def check_pass(self):
        moves = [n for n in VALID_COORDS if self.get_flipped(n, self.turn, self.board)]
        if not moves:
            opp = 'white' if self.turn == 'black' else 'black'
            if not any(self.get_flipped(n, opp, self.board) for n in VALID_COORDS):
                self.end_game()
            else:
                p_name = "黒" if self.turn == 'black' else "白"
                self.pass_msg = f"【{p_name}はパス】"
                self.history.append({'board': self.board.copy(), 'turn': self.turn, 'last_move': self.last_move})
                self.turn = opp
                self.draw()
                if self.mode == "PvE" and self.turn == self.cpu_color:
                    window.setTimeout(create_proxy(self.cpu_move), 800)
        elif self.mode == "PvE" and self.turn == self.cpu_color:
            window.setTimeout(create_proxy(self.cpu_move), 600)

    def end_game(self):
        self.is_game_over = True
        b = list(self.board.values()).count('black')
        w = list(self.board.values()).count('white')
        winner = "黒の勝ち！" if b > w else "白の勝ち！" if w > b else "引き分け"
        self.result_label.innerText = winner
        self.result_label.style.display = "block"
        self.draw()

    def undo(self):
        if not self.history: return
        self.is_game_over = False
        self.result_label.style.display = "none"
        steps = 2 if self.mode == "PvE" and len(self.history) >= 2 else 1
        for _ in range(steps):
            if self.history:
                s = self.history.pop()
                self.board, self.turn, self.last_move = s['board'], s['turn'], s['last_move']
        self.pass_msg = ""
        self.draw()

    # --- UIイベント接続 ---
    def handle_click(self, event):
        if self.is_game_over: return
        if self.mode == "PvE" and self.turn == self.cpu_color: return
        
        rect = self.canvas.getBoundingClientRect()
        scale_x = self.canvas.width / rect.width
        scale_y = self.canvas.height / rect.height
        x = (event.clientX - rect.left) * scale_x
        y = (event.clientY - rect.top) * scale_y
        
        best, min_dist = None, self.cell_size * 0.5
        for c in VALID_COORDS:
            nx = self.offset + c[0] * self.cell_size
            ny = self.offset + c[1] * self.cell_size
            d = math.hypot(nx - x, ny - y)
            if d < min_dist:
                min_dist, best = d, c
        if best: self.make_move(best)

    def setup_ui_events(self):
        # 盤面クリック
        self.canvas.onclick = create_proxy(self.handle_click)
        
        # ゲーム内ボタン
        document.getElementById("undo-btn").onclick = create_proxy(lambda e: self.undo())
        document.getElementById("reset-btn").onclick = create_proxy(lambda e: self.reset_game())
        document.getElementById("menu-btn").onclick = create_proxy(lambda e: self.show_menu())
        
        # メニュー画面ボタン
        document.getElementById("btn-pvp").onclick = create_proxy(lambda e: self.start_game("PvP"))
        document.getElementById("btn-pve").onclick = create_proxy(lambda e: self.start_game("PvE"))

    def start_game(self, mode):
        self.mode = mode
        # JS側のグローバル変数から設定を取得
        self.cpu_color = window.cpuColor
        self.level = window.selectedLv
        document.getElementById("menu-screen").style.display = "none"
        document.getElementById("game-screen").style.display = "block"
        self.reset_game()

    def show_menu(self):
        document.getElementById("game-screen").style.display = "none"
        document.getElementById("menu-screen").style.display = "block"

# 起動
game = NipWebGame()

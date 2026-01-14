import random
from itertools import combinations
from collections import defaultdict
import pandas as pd
from typing import List, Dict, Any, Tuple, Set

class AmericanoTournament:
    def __init__(self, players: List[str], num_fields: int):
        self.players = players
        self.num_players = len(players)
        self.num_fields = num_fields
        
        # Seguimiento de parejas únicas (N-1 partidos para cada uno)
        self.partner_count = defaultdict(lambda: defaultdict(int))
        self.opponent_count = defaultdict(lambda: defaultdict(int))
        self.games_played = defaultdict(int)  # Válidos
        self.helper_games = defaultdict(int) # Ayudante
        
        # La meta: todos deben ser pareja de todos exactamente 1 vez
        self.target_valid_games = self.num_players - 1
        self.todas_parejas_posibles = set(tuple(sorted(p)) for p in combinations(self.players, 2))
        self.parejas_cubiertas = set()

    def get_match_score(self, match: Tuple[str, str, str, str]) -> float:
        """Puntúa un partido para maximizar parejas y oponentes nuevos."""
        p1, p2, p3, p4 = match
        score = 0.0
        
        # Prioridad 1: Parejas que NO han jugado juntas
        if self.partner_count[p1][p2] == 0: score -= 50000
        if self.partner_count[p3][p4] == 0: score -= 50000
        
        # Prioridad 2: Oponentes que NO se han enfrentado
        new_opponents = 0
        for t1 in [p1, p2]:
            for t2 in [p3, p4]:
                if self.opponent_count[t1][t2] == 0:
                    new_opponents += 1
        score -= new_opponents * 1000
        
        # Prioridad 3: Balance de carga (que jueguen los que menos partidos totales llevan)
        total_load = sum(self.games_played[p] + self.helper_games[p] for p in match)
        score += total_load * 100
        
        return score

    def generate_tournament(self) -> Tuple[List[List[Dict]], Dict]:
        tournament_schedule = []
        max_rounds = 100 # Límite de seguridad
        round_num = 0

        # El torneo sigue MIENTRAS falten parejas por cubrir
        while len(self.parejas_cubiertas) < len(self.todas_parejas_posibles) and round_num < max_rounds:
            matches_this_round = []
            playing_this_round = set()
            
            # 1. Intentamos llenar las canchas con jugadores que aún necesitan partidos válidos
            for field_idx in range(self.num_fields):
                # Candidatos: personas que aún no tienen todas sus parejas y no están jugando en esta ronda
                candidates = [p for p in self.players if p not in playing_this_round]
                if not candidates: break

                best_match = None
                best_score = float('inf')
                helpers_in_match = []

                # OPCIÓN A: Buscar un partido de 4 personas que necesiten puntos válidos
                available_needing_games = [p for p in candidates if self.games_played[p] < self.target_valid_games]
                
                if len(available_needing_games) >= 4:
                    # Probamos combinaciones aleatorias de los que necesitan jugar
                    for _ in range(200):
                        combo = tuple(random.sample(available_needing_games, 4))
                        for config in [(combo[0], combo[1], combo[2], combo[3]), 
                                      (combo[0], combo[2], combo[1], combo[3])]:
                            score = self.get_match_score(config)
                            if score < best_score:
                                best_score = score
                                best_match = config
                                helpers_in_match = []

                # OPCIÓN B: Si no hay 4, forzamos a una pareja que FALTE y llenamos con ayudantes
                if not best_match or best_score > -10000:
                    faltantes_disponibles = [pair for pair in (self.todas_parejas_posibles - self.parejas_cubiertas)
                                           if pair[0] in candidates and pair[1] in candidates]
                    
                    if faltantes_disponibles:
                        p_a, p_b = random.choice(faltantes_disponibles)
                        # Buscamos 2 ayudantes (los que menos han jugado en total esta ronda)
                        others = [p for p in candidates if p not in (p_a, p_b)]
                        others.sort(key=lambda p: self.games_played[p] + self.helper_games[p])
                        
                        if len(others) >= 2:
                            best_match = (p_a, p_b, others[0], others[1])
                            helpers_in_match = [others[0], others[1]]

                if best_match:
                    # Validar quién es ayudante realmente (si la pareja ya jugó, son ayudantes)
                    p1, p2, p3, p4 = best_match
                    actual_helpers = set(helpers_in_match)
                    if self.partner_count[p1][p2] > 0: actual_helpers.update([p1, p2])
                    if self.partner_count[p3][p4] > 0: actual_helpers.update([p3, p4])

                    matches_this_round.append({
                        "players": best_match,
                        "helpers": list(actual_helpers),
                        "field": field_idx
                    })
                    
                    # Actualizar estadísticas al momento para que la siguiente cancha sepa qué falta
                    self.update_stats(best_match, list(actual_helpers))
                    playing_this_round.update(best_match)

            if not matches_this_round: # Si no se pudo armar ningún partido útil
                break
                
            tournament_schedule.append(matches_this_round)
            round_num += 1

        return tournament_schedule, {"total_rounds": len(tournament_schedule)}

    def update_stats(self, players, helpers):
        p1, p2, p3, p4 = players
        # Solo suma como pareja válida si no son ayudantes en este match
        self.partner_count[p1][p2] += 1; self.partner_count[p2][p1] += 1
        self.partner_count[p3][p4] += 1; self.partner_count[p4][p3] += 1
        
        self.parejas_cubiertas.add(tuple(sorted((p1, p2))))
        self.parejas_cubiertas.add(tuple(sorted((p3, p4))))
        
        # Oponentes
        for t1 in [p1, p2]:
            for t2 in [p3, p4]:
                self.opponent_count[t1][t2] += 1; self.opponent_count[t2][t1] += 1
        
        # Conteo de partidos
        for p in players:
            if p in helpers:
                self.helper_games[p] += 1
            else:
                self.games_played[p] += 1

    def format_for_streamlit(self, schedule, stats):
        rondas = []
        for i, matches in enumerate(schedule):
            partidos = []
            playing = set()
            for m in matches:
                p1, p2, p3, p4 = m["players"]
                playing.update([p1, p2, p3, p4])
                partidos.append({
                    "cancha": m["field"] + 1,
                    "pareja1": [p1, p2], "pareja2": [p3, p4],
                    "ayudantes": m["helpers"],
                    "valido_para": [p for p in [p1, p2, p3, p4] if p not in m["helpers"]]
                })
            rondas.append({
                "ronda": i + 1,
                "partidos": partidos,
                "descansan": [p for p in self.players if p not in playing]
            })
        
        resumen_df = pd.DataFrame([{
            "jugador": p, 
            "partidos_validos": self.games_played[p],
            "partidos_ayuda": self.helper_games[p],
            "total": self.games_played[p] + self.helper_games[p]
        } for p in self.players])

        return {"rondas": rondas, "resumen": resumen_df, "stats": stats}

def generar_torneo_todos_contra_todos(jugadores, num_canchas, seed=None):
    if seed: random.seed(seed)
    tournament = AmericanoTournament(jugadores, num_canchas)
    schedule, stats = tournament.generate_tournament()
    return tournament.format_for_streamlit(schedule, stats)
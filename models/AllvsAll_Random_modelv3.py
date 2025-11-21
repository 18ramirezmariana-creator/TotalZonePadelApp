import random
from itertools import combinations
from collections import defaultdict
import pandas as pd
from typing import List, Dict, Any, Tuple, Set

class AmericanoTournament:
    def __init__(self, players: List[str], num_fields: int):
        """
        Initialize Americano Padel Tournament
        
        Args:
            players: List of player names
            num_fields: Number of available padel fields
        """
        self.players = players
        self.num_players = len(players)
        self.num_fields = num_fields
        
        # Statistics tracking
        self.partner_count = defaultdict(lambda: defaultdict(int))
        self.opponent_count = defaultdict(lambda: defaultdict(int))
        self.games_played = defaultdict(int)  # Valid games only
        self.helper_games = defaultdict(int)  # Helper games (don't count)
        self.consecutive_rests = defaultdict(int)
        self.last_round_played = defaultdict(lambda: -1)
        
    def calculate_optimal_rounds(self) -> int:
        """Calculate optimal number of rounds based on Priority 1"""
        if self.num_fields == 2:
            # Priority 1: j-1 rounds for 2 fields
            return self.num_players - 1
        else:
            # For more fields: calculate to achieve all vs all
            players_per_round = self.num_fields * 4
            return max(self.num_players - 1, 
                      (self.num_players * (self.num_players - 1)) // (players_per_round * 2))
    
    def calculate_target_games(self) -> int:
        """
        Calculate target valid games per player based on Priority 2
        This should be the MINIMUM games everyone can achieve
        """
        total_rounds = self.calculate_optimal_rounds()
        total_slots = total_rounds * self.num_fields * 4
        # Calculate floor division to ensure everyone can reach this
        base_target = total_slots // self.num_players
        
        # Verify: can everyone play this many games?
        # We need base_target * num_players <= total_slots
        return base_target
    
    def get_uncovered_opponents(self, player: str) -> Set[str]:
        """Get list of players this player hasn't faced yet"""
        all_opponents = set(self.players) - {player}
        faced = set(p for p in all_opponents if self.opponent_count[player][p] > 0)
        return all_opponents - faced
    
    def get_uncovered_partners(self, player: str) -> Set[str]:
        """Get list of players this player hasn't partnered with yet"""
        all_partners = set(self.players) - {player}
        partnered = set(p for p in all_partners if self.partner_count[player][p] > 0)
        return all_partners - partnered
    
    def count_new_matchups(self, match: Tuple[str, str, str, str]) -> int:
        """Count how many NEW opponent matchups this match creates"""
        p1, p2, p3, p4 = match
        new_matchups = 0
        
        # Check all opponent pairs
        for t1_player in [p1, p2]:
            for t2_player in [p3, p4]:
                if self.opponent_count[t1_player][t2_player] == 0:
                    new_matchups += 1
        
        return new_matchups
    
    def count_new_partnerships(self, match: Tuple[str, str, str, str]) -> int:
        """Count how many NEW partnerships this match creates"""
        p1, p2, p3, p4 = match
        new_partnerships = 0
        
        if self.partner_count[p1][p2] == 0:
            new_partnerships += 1
        if self.partner_count[p3][p4] == 0:
            new_partnerships += 1
        
        return new_partnerships
    
    def get_match_score(self, match: Tuple[str, str, str, str], round_num: int, is_helper_match: bool = False) -> float:
        """
        Score a potential match based on priorities
        Lower score is better
        """
        p1, p2, p3, p4 = match
        score = 0.0
        
        # If this is a helper match, deprioritize it heavily
        if is_helper_match:
            score += 10000
        
        # NEW: Count new matchups (highest priority after helpers)
        new_matchups = self.count_new_matchups(match)
        new_partnerships = self.count_new_partnerships(match)
        
        # Heavily reward new opponent matchups (Priority 4 enhancement)
        score -= new_matchups * 2500  # Each new opponent matchup is highly valuable
        
        # Reward new partnerships strongly
        score -= new_partnerships * 3000  # New partnerships are critical
        
        # Penalize repeated partnerships heavily
        partner_reps = self.partner_count[p1][p2] + self.partner_count[p3][p4]
        if partner_reps > 0:
            score += partner_reps * 5000  # Much higher penalty for repeating
        
        # Penalize repeated opponent matchups moderately
        opponents = [(p1, p3), (p1, p4), (p2, p3), (p2, p4)]
        total_opponent_reps = sum(self.opponent_count[opp1][opp2] for opp1, opp2 in opponents)
        if total_opponent_reps > 0:
            score += total_opponent_reps * 800
        
        # Priority 3: Avoid consecutive rests
        for p in match:
            if self.last_round_played[p] == round_num - 1:
                score += 300
            elif self.last_round_played[p] < round_num - 1:
                score -= 200
        
        # Priority 2: Balance games played
        games_sum = sum(self.games_played[p] for p in match)
        score += games_sum * 400
        
        # Minimize variance in games played within this match
        games_list = [self.games_played[p] for p in match]
        variance = max(games_list) - min(games_list)
        score += variance * 300
        
        return score
    
    def select_helpers(self, needed: int, available_players: Set[str], round_num: int) -> List[str]:
        """
        Select helper players to complete a match
        Helpers are players who already have enough valid games
        """
        target_games = self.calculate_target_games()
        
        # Candidates: players NOT in available (they're resting or already playing)
        # AND players who already have target games or more
        candidates = []
        
        for p in self.players:
            if p not in available_players and self.games_played[p] >= target_games:
                candidates.append(p)
        
        # If not enough candidates with target games, allow anyone not available
        if len(candidates) < needed:
            candidates = [p for p in self.players if p not in available_players]
        
        # Sort by: most valid games (they can afford to help), least helper games (fair distribution)
        candidates.sort(key=lambda p: (-self.games_played[p], self.helper_games[p]))
        
        return candidates[:needed]
    
    def generate_round_matches(self, round_num: int, available_players: List[str]) -> Tuple[List[Dict], List[str]]:
        """Generate matches for a round, using helpers if needed"""
        matches = []
        remaining = set(available_players)
        target_games = self.calculate_target_games()
        
        for field_idx in range(self.num_fields):
            if len(remaining) == 0:
                break
            
            players_needing_games = [p for p in remaining if self.games_played[p] < target_games]
            
            helpers_needed = []
            is_helper_match = False
            
            if len(players_needing_games) >= 4:
                # ENHANCED: Greedy + sampling approach for better coverage
                best_match = None
                best_score = float('inf')
                
                candidates = players_needing_games
                
                # Strategy 1: Prioritize players with most uncovered opponents
                players_by_coverage = sorted(
                    candidates, 
                    key=lambda p: (
                        -len(self.get_uncovered_opponents(p)),
                        -len(self.get_uncovered_partners(p)),
                        self.games_played[p]
                    )
                )
                
                # Try focused combinations first (players who need coverage)
                focused_tries = 0
                max_focused = min(100, len(list(combinations(players_by_coverage[:8], 4))))
                
                for combo in combinations(players_by_coverage[:8], 4):
                    if focused_tries >= max_focused:
                        break
                    focused_tries += 1
                    
                    p1, p2, p3, p4 = combo
                    configurations = [
                        (p1, p2, p3, p4),
                        (p1, p3, p2, p4),
                        (p1, p4, p2, p3),
                    ]
                    
                    for config in configurations:
                        score = self.get_match_score(config, round_num, False)
                        if score < best_score:
                            best_score = score
                            best_match = config
                
                # Strategy 2: Random sampling for diversity
                if len(candidates) > 8:
                    for _ in range(100):
                        combo = tuple(random.sample(candidates, 4))
                        p1, p2, p3, p4 = combo
                        
                        configurations = [
                            (p1, p2, p3, p4),
                            (p1, p3, p2, p4),
                            (p1, p4, p2, p3),
                        ]
                        
                        for config in configurations:
                            score = self.get_match_score(config, round_num, False)
                            if score < best_score:
                                best_score = score
                                best_match = config
                
                if best_match:
                    matches.append({
                        "players": best_match,
                        "helpers": [],
                        "field": field_idx
                    })
                    remaining -= set(best_match)
                    
            elif len(players_needing_games) > 0:
                # Match with helpers
                regular_players = players_needing_games
                need_helpers = 4 - len(regular_players)
                is_helper_match = True
                
                available_helpers_from_remaining = [
                    p for p in remaining 
                    if p not in regular_players and self.games_played[p] >= target_games
                ]
                
                if len(available_helpers_from_remaining) >= need_helpers:
                    helpers_needed = available_helpers_from_remaining[:need_helpers]
                else:
                    helpers_needed = available_helpers_from_remaining + self.select_helpers(
                        need_helpers - len(available_helpers_from_remaining), 
                        remaining, 
                        round_num
                    )
                
                if len(helpers_needed) < need_helpers:
                    break
                
                all_players = regular_players + helpers_needed
                
                # Even with helpers, optimize for coverage
                best_config = None
                best_score = float('inf')
                
                import itertools
                for perm in itertools.permutations(all_players, 4):
                    p1, p2, p3, p4 = perm
                    configurations = [
                        (p1, p2, p3, p4),
                        (p1, p3, p2, p4),
                        (p1, p4, p2, p3),
                    ]
                    
                    for config in configurations:
                        score = self.get_match_score(config, round_num, True)
                        if score < best_score:
                            best_score = score
                            best_config = config
                
                if best_config:
                    matches.append({
                        "players": best_config,
                        "helpers": helpers_needed,
                        "field": field_idx
                    })
                    for p in best_config:
                        if p in remaining:
                            remaining.discard(p)
            else:
                break
        
        resting = list(remaining)
        return matches, resting
    
    def update_statistics(self, match: Dict, round_num: int):
        """Update tracking statistics after a match"""
        p1, p2, p3, p4 = match["players"]
        helpers = match["helpers"]
        
        # Update partners
        self.partner_count[p1][p2] += 1
        self.partner_count[p2][p1] += 1
        self.partner_count[p3][p4] += 1
        self.partner_count[p4][p3] += 1
        
        # Update opponents
        for t1_player in [p1, p2]:
            for t2_player in [p3, p4]:
                self.opponent_count[t1_player][t2_player] += 1
                self.opponent_count[t2_player][t1_player] += 1
        
        # Update games played
        for p in [p1, p2, p3, p4]:
            if p in helpers:
                self.helper_games[p] += 1
            else:
                self.games_played[p] += 1
            self.last_round_played[p] = round_num
    
    def generate_tournament(self) -> Tuple[List[List[Dict]], Dict]:
        """Generate complete tournament schedule"""
        num_rounds = self.calculate_optimal_rounds()
        tournament_schedule = []
        
        for round_num in range(num_rounds):
            # All players available, prioritize those with fewer games and rested
            available = sorted(self.players, 
                             key=lambda p: (self.games_played[p], 
                                          -self.consecutive_rests[p],
                                          round_num - self.last_round_played[p]))
            
            matches, resting = self.generate_round_matches(round_num, available)
            
            if not matches:
                break
                
            tournament_schedule.append(matches)
            
            for match in matches:
                self.update_statistics(match, round_num)
            
            # Update consecutive rests
            for p in resting:
                self.consecutive_rests[p] += 1
            for match in matches:
                for p in match["players"]:
                    self.consecutive_rests[p] = 0
        
        stats = {
            "games_played": dict(self.games_played),
            "helper_games": dict(self.helper_games),
            "target_games": self.calculate_target_games()
        }
        
        return tournament_schedule, stats
    
    def format_for_streamlit(self, tournament_schedule: List[List[Dict]], 
                            stats: Dict) -> Dict[str, Any]:
        """
        Format tournament output for Streamlit visualization
        Returns structure compatible with Streamlit code
        """
        rondas = []
        
        for round_num, matches in enumerate(tournament_schedule, 1):
            playing = set()
            for match in matches:
                playing.update(match["players"])
            descansan = [p for p in self.players if p not in playing]
            
            partidos = []
            for match in matches:
                p1, p2, p3, p4 = match["players"]
                helpers = match["helpers"]
                
                # valido_para: all players except helpers
                valido_para = [p for p in [p1, p2, p3, p4] if p not in helpers]
                
                partido = {
                    "cancha": match["field"] + 1,
                    "pareja1": [p1, p2],
                    "pareja2": [p3, p4],
                    "ayudantes": helpers,
                    "valido_para": valido_para
                }
                partidos.append(partido)
            
            ronda_data = {
                "ronda": round_num,
                "partidos": partidos,
                "descansan": descansan
            }
            rondas.append(ronda_data)
        
        # Create summary DataFrame
        resumen_data = []
        for player in self.players:
            valid_games = self.games_played[player]
            helper_games_count = self.helper_games[player]
            total_games = valid_games + helper_games_count
            
            resumen_data.append({
                "jugador": player,
                "partidos_totales": total_games,
                "partidos_validos": valid_games,
                "partidos_ayudante": helper_games_count
            })
        
        resumen_df = pd.DataFrame(resumen_data)
        
        output = {
            "rondas": rondas,
            "resumen": resumen_df,
            "stats": {
                "total_rounds": len(rondas),
                "players": self.num_players,
                "fields": self.num_fields,
                "target_games": stats["target_games"],
                "games_distribution": stats["games_played"],
                "helper_distribution": stats["helper_games"]
            }
        }
        
        return output


def generar_torneo_todos_contra_todos(jugadores: List[str], num_canchas: int, 
                                      seed: int = None) -> Dict[str, Any]:
    """
    Main function to generate tournament compatible with Streamlit app
    
    Args:
        jugadores: List of player names
        num_canchas: Number of fields/courts available
        seed: Random seed (optional, for reproducibility)
    
    Returns:
        Dictionary with 'rondas', 'resumen', and 'stats'
    """
    if seed:
        random.seed(seed)
    
    tournament = AmericanoTournament(jugadores, num_canchas)
    schedule, stats = tournament.generate_tournament()
    return tournament.format_for_streamlit(schedule, stats)
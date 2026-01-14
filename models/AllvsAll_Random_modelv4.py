""" version todos contra todos y con todos - claude"""
import random
from itertools import combinations
from collections import defaultdict
import pandas as pd
from typing import List, Dict, Any, Tuple, Set

class CompleteAmericanoTournament:
    def __init__(self, players: List[str], num_fields: int):
        """
        Initialize Complete Coverage Americano Tournament
        Guarantees every player faces and partners with every other player
        
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
        self.games_played = defaultdict(int)
        self.helper_games = defaultdict(int)
        self.consecutive_rests = defaultdict(int)
        self.last_round_played = defaultdict(lambda: -1)
        
    def calculate_minimum_games_needed(self) -> int:
        """
        Calculate minimum games needed to face everyone as opponent AND partner
        Each player needs to:
        - Face (n-1) players as opponents (2 opponents per game)
        - Partner with (n-1) players as partners (1 partner per game)
        
        For opponents: need ceil((n-1)/2) games minimum
        For partners: need (n-1) games minimum
        So minimum is (n-1) games per player
        """
        return self.num_players - 1
    
    def calculate_optimal_rounds(self) -> int:
        """
        Calculate rounds needed to ensure everyone gets minimum games
        """
        min_games = self.calculate_minimum_games_needed()
        total_game_slots_needed = self.num_players * min_games
        slots_per_round = self.num_fields * 4
        
        # Round up to ensure enough slots
        rounds_needed = (total_game_slots_needed + slots_per_round - 1) // slots_per_round
        
        # Add buffer rounds for better coverage (harder to achieve perfect coverage in exact minimum)
        return rounds_needed + max(2, self.num_players // 4)
    
    def get_uncovered_opponents(self, player: str) -> Set[str]:
        """Get players this player hasn't faced as opponent yet"""
        all_others = set(self.players) - {player}
        faced = set(p for p in all_others if self.opponent_count[player][p] > 0)
        return all_others - faced
    
    def get_uncovered_partners(self, player: str) -> Set[str]:
        """Get players this player hasn't partnered with yet"""
        all_others = set(self.players) - {player}
        partnered = set(p for p in all_others if self.partner_count[player][p] > 0)
        return all_others - partnered
    
    def is_complete_coverage(self, player: str) -> bool:
        """Check if player has faced and partnered with everyone"""
        uncovered_opponents = self.get_uncovered_opponents(player)
        uncovered_partners = self.get_uncovered_partners(player)
        return len(uncovered_opponents) == 0 and len(uncovered_partners) == 0
    
    def count_coverage_created(self, match: Tuple[str, str, str, str]) -> Dict[str, int]:
        """
        Count new opponent and partner matchups this match creates
        Returns dict with 'opponents' and 'partners' counts
        """
        p1, p2, p3, p4 = match
        new_opponents = 0
        new_partners = 0
        
        # Check opponent pairs
        for t1_player in [p1, p2]:
            for t2_player in [p3, p4]:
                if self.opponent_count[t1_player][t2_player] == 0:
                    new_opponents += 1
        
        # Check partnerships
        if self.partner_count[p1][p2] == 0:
            new_partners += 1
        if self.partner_count[p3][p4] == 0:
            new_partners += 1
        
        return {"opponents": new_opponents, "partners": new_partners}
    
    def get_match_score(self, match: Tuple[str, str, str, str], 
                       round_num: int, is_helper_match: bool = False) -> float:
        """
        Score a potential match based on complete coverage priority
        Lower score is better
        """
        p1, p2, p3, p4 = match
        score = 0.0
        
        # CRITICAL: Helper matches should only be used when absolutely necessary
        if is_helper_match:
            score += 100000
        
        # Count coverage created
        coverage = self.count_coverage_created(match)
        
        # HIGHEST PRIORITY: New opponent matchups
        score -= coverage["opponents"] * 5000
        
        # SECOND PRIORITY: New partnerships
        score -= coverage["partners"] * 4000
        
        # HEAVY penalty for repeating partnerships (waste of limited games)
        partner_reps = self.partner_count[p1][p2] + self.partner_count[p3][p4]
        if partner_reps > 0:
            score += partner_reps * 8000
        
        # Moderate penalty for repeating opponent matchups
        opponents = [(p1, p3), (p1, p4), (p2, p3), (p2, p4)]
        total_opponent_reps = sum(self.opponent_count[opp1][opp2] for opp1, opp2 in opponents)
        if total_opponent_reps > 0:
            score += total_opponent_reps * 1500
        
        # Prioritize players who need more coverage
        total_uncovered = sum(
            len(self.get_uncovered_opponents(p)) + len(self.get_uncovered_partners(p))
            for p in match
        )
        score -= total_uncovered * 300
        
        # Balance games played (but lower priority than coverage)
        games_variance = max(self.games_played[p] for p in match) - min(self.games_played[p] for p in match)
        score += games_variance * 200
        
        # Slight preference for rested players
        for p in match:
            if self.last_round_played[p] < round_num - 1:
                score -= 50
        
        return score
    
    def generate_round_matches(self, round_num: int, available_players: List[str]) -> Tuple[List[Dict], List[str]]:
        """Generate matches for a round, minimizing helper usage"""
        matches = []
        remaining = set(available_players)
        min_games = self.calculate_minimum_games_needed()
        
        for field_idx in range(self.num_fields):
            if len(remaining) < 4:
                break
            
            # Prioritize players who haven't reached minimum games
            players_needing_games = [p for p in remaining if self.games_played[p] < min_games]
            
            if len(players_needing_games) >= 4:
                # Regular match - no helpers needed
                best_match = None
                best_score = float('inf')
                
                # Strategy 1: Prioritize players with most uncovered matchups
                players_by_need = sorted(
                    players_needing_games,
                    key=lambda p: (
                        -(len(self.get_uncovered_opponents(p)) + len(self.get_uncovered_partners(p))),
                        self.games_played[p]
                    )
                )
                
                # Try combinations of players who most need coverage
                search_pool = players_by_need[:min(12, len(players_by_need))]
                tried = 0
                max_tries = min(200, len(list(combinations(search_pool, 4))))
                
                for combo in combinations(search_pool, 4):
                    if tried >= max_tries:
                        break
                    tried += 1
                    
                    # Try different team configurations
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
                
                # Random sampling for diversity
                if len(players_needing_games) > 12:
                    for _ in range(150):
                        combo = tuple(random.sample(players_needing_games, 4))
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
                # Only use helpers if we have 1-3 players needing games left
                # This minimizes helper usage
                need_helpers = 4 - len(players_needing_games)
                
                # Select helpers: players who have complete coverage
                potential_helpers = [
                    p for p in remaining 
                    if p not in players_needing_games and self.is_complete_coverage(p)
                ]
                
                # If not enough with complete coverage, use those with most games
                if len(potential_helpers) < need_helpers:
                    potential_helpers = [
                        p for p in remaining if p not in players_needing_games
                    ]
                    potential_helpers.sort(key=lambda p: -self.games_played[p])
                
                helpers = potential_helpers[:need_helpers]
                
                if len(helpers) == need_helpers:
                    all_players = players_needing_games + helpers
                    
                    # Optimize configuration even with helpers
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
                            "helpers": helpers,
                            "field": field_idx
                        })
                        for p in best_config:
                            if p in remaining:
                                remaining.discard(p)
        
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
    
    def check_coverage_status(self) -> Dict[str, Any]:
        """Check coverage completion for all players"""
        status = {}
        for player in self.players:
            uncovered_opponents = self.get_uncovered_opponents(player)
            uncovered_partners = self.get_uncovered_partners(player)
            status[player] = {
                "games_played": self.games_played[player],
                "uncovered_opponents": len(uncovered_opponents),
                "uncovered_partners": len(uncovered_partners),
                "complete": len(uncovered_opponents) == 0 and len(uncovered_partners) == 0
            }
        return status
    
    def generate_tournament(self) -> Tuple[List[List[Dict]], Dict]:
        """Generate complete tournament schedule"""
        num_rounds = self.calculate_optimal_rounds()
        tournament_schedule = []
        
        for round_num in range(num_rounds):
            # Check if everyone has complete coverage
            coverage_status = self.check_coverage_status()
            all_complete = all(status["complete"] for status in coverage_status.values())
            
            if all_complete:
                #print(f"Complete coverage achieved at round {round_num + 1}")
                break
            
            # Prioritize players who need coverage most
            available = sorted(
                self.players,
                key=lambda p: (
                    -(coverage_status[p]["uncovered_opponents"] + coverage_status[p]["uncovered_partners"]),
                    self.games_played[p],
                    -self.consecutive_rests[p]
                )
            )
            
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
        
        # Final coverage check
        final_coverage = self.check_coverage_status()
        
        stats = {
            "games_played": dict(self.games_played),
            "helper_games": dict(self.helper_games),
            "minimum_games": self.calculate_minimum_games_needed(),
            "coverage_status": final_coverage
        }
        
        return tournament_schedule, stats
    
    def format_for_streamlit(self, tournament_schedule: List[List[Dict]], 
                            stats: Dict = None) -> Dict[str, Any]:
        """
        Format tournament output for Streamlit visualization
        
        Args:
            tournament_schedule: List of rounds with matches
            stats: Tournament statistics (optional for backward compatibility)
        """
        # If stats not provided, calculate from current state
        if stats is None:
            stats = {
                "games_played": dict(self.games_played),
                "helper_games": dict(self.helper_games),
                "minimum_games": self.calculate_minimum_games_needed(),
                "coverage_status": self.check_coverage_status()
            }
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
            
            coverage = stats["coverage_status"][player]
            
            resumen_data.append({
                "jugador": player,
                "partidos_totales": total_games,
                "partidos_validos": valid_games,
                "partidos_ayudante": helper_games_count,
                "rivales_pendientes": coverage["uncovered_opponents"],
                "parejas_pendientes": coverage["uncovered_partners"],
                "cobertura_completa": "✓" if coverage["complete"] else "✗"
            })
        
        resumen_df = pd.DataFrame(resumen_data)
        
        output = {
            "rondas": rondas,
            "resumen": resumen_df,
            "stats": {
                "total_rounds": len(rondas),
                "players": self.num_players,
                "fields": self.num_fields,
                "minimum_games": stats["minimum_games"],
                "games_distribution": stats["games_played"],
                "helper_distribution": stats["helper_games"],
                "coverage_status": stats["coverage_status"]
            }
        }
        
        return output


def generar_torneo_cobertura_completa(jugadores: List[str], num_canchas: int, 
                                      seed: int = None) -> Dict[str, Any]:
    """
    Generate tournament guaranteeing everyone plays with and against everyone
    
    COMPATIBLE with existing Streamlit code that expects:
        tournament.format_for_streamlit(schedule, helpers)
    
    Args:
        jugadores: List of player names
        num_canchas: Number of fields/courts available
        seed: Random seed (optional, for reproducibility)
    
    Returns:
        Dictionary with 'rondas', 'resumen', and 'stats'
    """
    if seed:
        random.seed(seed)
    
    tournament = CompleteAmericanoTournament(jugadores, num_canchas)
    schedule, stats = tournament.generate_tournament()
    return tournament.format_for_streamlit(schedule, stats)

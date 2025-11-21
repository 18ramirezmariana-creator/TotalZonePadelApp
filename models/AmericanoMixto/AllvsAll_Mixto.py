from collections import defaultdict
import random

class AmericanoPadelTournament:
    def __init__(self, male_players, female_players, num_fields, points_per_match):
        """
        Initialize the Americano Padel Tournament
        
        Args:
            male_players (list): List of male player names
            female_players (list): List of female player names
            num_fields (int): Number of available courts/fields
            points_per_match (int): Winning format (e.g., 24, 32 points)
        """
        # Validate equal numbers
        if len(male_players) != len(female_players):
            raise ValueError(f"Must have equal numbers of men and women. Got {len(male_players)} men and {len(female_players)} women.")
        
        if len(male_players) < 2:
            raise ValueError("Need at least 2 players of each gender (4 total)")
        
        self.male_players = male_players
        self.female_players = female_players
        self.num_players = len(male_players)  # Players per gender
        self.total_players = len(male_players) + len(female_players)
        self.num_fields = num_fields
        self.points_per_match = points_per_match
        
        # Track statistics for each player
        self.player_stats = defaultdict(lambda: {
            'matches': 0,
            'partners': defaultdict(int),  # How many times partnered with each player
            'opponents': defaultdict(int),  # How many times opposed each player
            'points_for': 0,
            'points_against': 0
        })
        
        self.rounds = []
        self.all_matches_played = set()  # Track unique matches
    
    def get_match_signature(self, team1, team2):
        """Create unique signature for a match (independent of team/player order)"""
        all_players = sorted([team1[0], team1[1], team2[0], team2[1]])
        return tuple(all_players)
    
    def calculate_match_score(self, team1, team2):
        """
        Calculate desirability score for a match (LOWER is better)
        Prioritizes:
        1. Players with fewer matches
        2. New partnerships
        3. New opponents
        """
        players = [team1[0], team1[1], team2[0], team2[1]]
        
        # Base score: sum of all players' match counts (prefer players with fewer matches)
        match_count_score = sum(self.player_stats[p]['matches'] for p in players)
        
        # Partnership penalty (heavily penalize repeated partnerships)
        partnership_penalty = 0
        partnership_penalty += self.player_stats[team1[0]]['partners'][team1[1]] * 1000
        partnership_penalty += self.player_stats[team2[0]]['partners'][team2[1]] * 1000
        
        # Opponent penalty (moderately penalize repeated opponents)
        opponent_penalty = 0
        for p1 in [team1[0], team1[1]]:
            for p2 in [team2[0], team2[1]]:
                opponent_penalty += self.player_stats[p1]['opponents'][p2] * 100
        
        total_score = match_count_score + partnership_penalty + opponent_penalty
        
        # Add small random factor to break ties
        total_score += random.random() * 0.01
        
        return total_score
    
    def find_best_matches_for_round(self, num_matches_needed):
        """
        Find the best set of matches for a round
        Uses greedy algorithm to select matches that maximize balance
        """
        selected_matches = []
        used_players = set()
        
        # Generate all possible matches from unused players
        while len(selected_matches) < num_matches_needed:
            available_males = [m for m in self.male_players if m not in used_players]
            available_females = [f for f in self.female_players if f not in used_players]
            
            # Need at least 2 of each gender
            if len(available_males) < 2 or len(available_females) < 2:
                break
            
            best_match = None
            best_score = float('inf')
            
            # Try all possible match combinations with available players
            for i in range(len(available_males)):
                for j in range(i + 1, len(available_males)):
                    m1, m2 = available_males[i], available_males[j]
                    
                    for k in range(len(available_females)):
                        for l in range(k + 1, len(available_females)):
                            f1, f2 = available_females[k], available_females[l]
                            
                            # Try both team configurations
                            configs = [
                                ((m1, f1), (m2, f2)),
                                ((m1, f2), (m2, f1))
                            ]
                            
                            for team1, team2 in configs:
                                signature = self.get_match_signature(team1, team2)
                                
                                # Skip if already played
                                if signature in self.all_matches_played:
                                    continue
                                
                                score = self.calculate_match_score(team1, team2)
                                
                                if score < best_score:
                                    best_score = score
                                    best_match = (team1, team2)
            
            if best_match is None:
                break
            
            selected_matches.append(best_match)
            team1, team2 = best_match
            used_players.update([team1[0], team1[1], team2[0], team2[1]])
            
            # Mark as played
            signature = self.get_match_signature(team1, team2)
            self.all_matches_played.add(signature)
        
        return selected_matches
    
    def update_player_stats(self, match):
        """Update statistics after a match is scheduled"""
        team1, team2 = match
        
        # Update match counts
        for player in [team1[0], team1[1], team2[0], team2[1]]:
            self.player_stats[player]['matches'] += 1
        
        # Update partnerships
        self.player_stats[team1[0]]['partners'][team1[1]] += 1
        self.player_stats[team1[1]]['partners'][team1[0]] += 1
        self.player_stats[team2[0]]['partners'][team2[1]] += 1
        self.player_stats[team2[1]]['partners'][team2[0]] += 1
        
        # Update opponents
        for p1 in [team1[0], team1[1]]:
            for p2 in [team2[0], team2[1]]:
                self.player_stats[p1]['opponents'][p2] += 1
                self.player_stats[p2]['opponents'][p1] += 1
    
    def generate_schedule(self, target_matches_per_player=None):
        """
        Generate the complete tournament schedule
        
        Args:
            target_matches_per_player (int): Target number of matches per player
                                            None = auto-calculate (total_players - 1)
        
        Example:
            tournament.generate_schedule()  # Auto-calculate target
            tournament.generate_schedule(target_matches_per_player=10)  # Specific target
        """
        # Calculate target matches
        if target_matches_per_player is None:
            # In a perfect Americano with equal genders:
            # Each player partners with n opposite-gender players
            # Against (n-1) other opposite-gender players each time
            # This gives approximately n*(n-1) total combinations to explore
            # But practical target is closer to (total_players - 1) for balance
            target_matches_per_player = self.total_players - 1
        
        print(f"{'='*70}")
        print(f"AMERICANO PADEL TOURNAMENT".center(70))
        print(f"{'='*70}")
        print(f"Players: {self.num_players} men + {self.num_players} women = {self.total_players} total")
        print(f"Available courts: {self.num_fields}")
        print(f"Points per match: {self.points_per_match}")
        print(f"Target matches per player: {target_matches_per_player}")
        print()
        
        round_num = 0
        consecutive_empty_rounds = 0
        
        while consecutive_empty_rounds < 3:  # Stop if can't generate matches for 3 rounds
            round_num += 1
            
            # Check if all players have reached target
            match_counts = [self.player_stats[p]['matches'] for p in 
                          self.male_players + self.female_players]
            min_matches = min(match_counts) if match_counts else 0
            max_matches = max(match_counts) if match_counts else 0
            
            # Stop if minimum target reached and balanced within 1 match
            if min_matches >= target_matches_per_player and (max_matches - min_matches) <= 1:
                print(f"Target reached! All players have {min_matches}-{max_matches} matches.")
                break
            
            # Generate matches for this round
            round_matches = self.find_best_matches_for_round(self.num_fields)
            
            if not round_matches:
                consecutive_empty_rounds += 1
                continue
            
            consecutive_empty_rounds = 0
            self.rounds.append(round_matches)
            
            # Update stats
            for match in round_matches:
                self.update_player_stats(match)
        
        return self.rounds
    
    def print_schedule(self):
        """Print the complete tournament schedule"""
        print(f"\n{'='*70}")
        print(f"TOURNAMENT SCHEDULE".center(70))
        print(f"{'='*70}\n")
        
        for round_num, round_matches in enumerate(self.rounds, 1):
            print(f"{'ROUND ' + str(round_num):^70}")
            print(f"{'-'*70}")
            
            for court_num, match in enumerate(round_matches, 1):
                team1, team2 = match
                print(f"  Court {court_num}: {team1[0]:12} & {team1[1]:12} vs "
                      f"{team2[0]:12} & {team2[1]:12}")
            
            print()
    
    def print_statistics(self):
        """Print detailed player statistics"""
        print(f"{'='*70}")
        print(f"PLAYER STATISTICS".center(70))
        print(f"{'='*70}\n")
        
        all_players = self.male_players + self.female_players
        
        # Sort by match count, then alphabetically
        sorted_players = sorted(all_players, 
                               key=lambda p: (-self.player_stats[p]['matches'], p))
        
        print(f"{'Player':<15} {'Matches':<10} {'Partners':<12} {'Opponents':<12}")
        print(f"{'-'*70}")
        
        for player in sorted_players:
            stats = self.player_stats[player]
            num_partners = len([p for p in stats['partners'] if stats['partners'][p] > 0])
            num_opponents = len([p for p in stats['opponents'] if stats['opponents'][p] > 0])
            
            print(f"{player:<15} {stats['matches']:<10} {num_partners:<12} {num_opponents:<12}")
        
        # Show balance metrics
        match_counts = [self.player_stats[p]['matches'] for p in all_players]
        print(f"\n{'Balance Metrics:':<20}")
        print(f"{'  Min matches:':<20} {min(match_counts)}")
        print(f"{'  Max matches:':<20} {max(match_counts)}")
        print(f"{'  Difference:':<20} {max(match_counts) - min(match_counts)}")
        print(f"{'  Total rounds:':<20} {len(self.rounds)}")

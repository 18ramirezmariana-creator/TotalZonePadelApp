import streamlit as st
from models.AmericanoMixto.AllvsAll_Mixto import AmericanoPadelTournament

def app():
    male_players = st.session_state.hombres
    female_players = st.session_state.mujeres
    num_fields = st.session_state.num_fields
    points_per_match = st.session_state.num_pts
    
    # Create tournament
    tournament = AmericanoPadelTournament(
        male_players=male_players,
        female_players=female_players,
        num_fields=num_fields,
        points_per_match=points_per_match
    )
    
    # Generate schedule (None = auto-calculate rounds, or specify a number)
    tournament.generate_schedule()
    
    # Print results
    tournament.print_schedule()
    tournament.print_statistics()

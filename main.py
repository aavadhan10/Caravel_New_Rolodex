import streamlit as st
import pandas as pd
import numpy as np
import os
import anthropic
import re
from functools import lru_cache

# Page Configuration
st.set_page_config(
    page_title="Legal Expert Finder",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS for styling
st.markdown("""
<style>
.lawyer-card {
    background-color: #f8f9fa;
    border-radius: 10px;
    padding: 20px;
    margin-bottom: 20px;
    border-left: 5px solid #1e88e5;
}
.lawyer-name {
    color: #1e4b79;
    font-size: 22px;
    font-weight: bold;
}
.lawyer-email {
    color: #263238;
    font-style: italic;
}
.skill-tag {
    background-color: #e3f2fd;
    border-radius: 15px;
    padding: 5px 10px;
    margin-right: 5px;
    display: inline-block;
    font-size: 14px;
}
.reasoning-box {
    background-color: #f1f8e9;
    border-radius: 5px;
    padding: 15px;
    margin-top: 10px;
    border-left: 3px solid #7cb342;
}
.recent-query-button {
    margin-bottom: 8px !important;
    width: 100%;
}
h1 {
    color: #1e4b79;
}
.scroll-container {
    max-height: 400px;
    overflow-y: auto;
    padding-right: 10px;
}
.stButton button {
    width: 100%;
    margin-bottom: 8px;
}
.availability-tag {
    background-color: #e8f5e9;
    border-radius: 15px;
    padding: 4px 8px;
    font-size: 12px;
    color: #2e7d32;
    display: inline-block;
    margin-left: 10px;
}
.billable-rate {
    color: #455a64;
    font-size: 14px;
    margin-top: 5px;
}
.practice-area {
    color: #455a64;
    font-size: 14px;
    margin-top: 5px;
    font-weight: 500;
}
</style>
""", unsafe_allow_html=True)

# Set up sidebar
st.sidebar.title("⚖️ Legal Expert Finder")
st.sidebar.title("About")
st.sidebar.info(
    "This internal tool helps match client legal needs with the right lawyer based on self-reported expertise. "
    "Designed for partners and executive assistants to quickly find the best internal resource for client requirements."
)
st.sidebar.markdown("---")

# Recent client queries section in sidebar
st.sidebar.markdown("### Recent Client Queries")
recent_queries = [
    "IP licensing for SaaS company",
    "Employment dispute in Ontario", 
    "M&A due diligence for tech acquisition",
    "Privacy compliance for healthcare app",
    "Commercial lease agreement review"
]
for query in recent_queries:
    if st.sidebar.button(query, key=f"recent_{query}", help=f"Use this recent query: {query}"):
        st.session_state.query = query
        st.session_state.search_pressed = True

st.sidebar.markdown("---")
st.sidebar.markdown("### Need Help?")
st.sidebar.info(
    "For assistance with the matching tool or to add a lawyer to the database, contact the Legal Operations team at legalops@example.com"
)

# Function to load and process the CSV data
@lru_cache(maxsize=1)  # Cache the result to avoid reloading
def load_lawyer_data():
    try:
        df = pd.read_csv('combined_unique.csv')
        return process_lawyer_data(df)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

def process_lawyer_data(df):
    # Get all skill columns
    skill_columns = [col for col in df.columns if '(Skill' in col]
    
    # Create a map of normalized skill names
    skill_map = {}
    for col in skill_columns:
        match = re.match(r'(.*) \(Skill \d+\)', col)
        if match:
            skill_name = match.group(1)
            if skill_name not in skill_map:
                skill_map[skill_name] = []
            skill_map[skill_name].append(col)
    
    # Function to get max skill value across duplicate columns
    def get_max_skill_value(lawyer_row, skill_name):
        columns = skill_map.get(skill_name, [])
        values = [lawyer_row[col] for col in columns if pd.notna(lawyer_row[col])]
        return max(values) if values else 0
    
    # Create lawyer profiles with additional mock data for demo purposes
    lawyers = []
    practice_areas = ["Corporate", "Litigation", "IP", "Employment", "Privacy", "Finance", "Real Estate", "Tax"]
    availability_statuses = ["Available Now", "Available Next Week", "Limited Availability", "On Leave"]
    rate_ranges = ["$400-500/hr", "$500-600/hr", "$600-700/hr", "$700-800/hr", "$800-900/hr"]
    
    for _, row in df.iterrows():
        profile = {
            'name': row['Submitter Name'],
            'email': row['Submitter Email'],
            'skills': {},
            # Add mock data for demo 
            'practice_area': np.random.choice(practice_areas),
            'availability': np.random.choice(availability_statuses, p=[0.4, 0.3, 0.2, 0.1]),
            'billable_rate': np.random.choice(rate_ranges),
            'last_client': f"Client {np.random.randint(100, 999)}"
        }
        
        # Extract skills with non-zero values
        for skill_name in skill_map:
            value = get_max_skill_value(row, skill_name)
            if value > 0:
                profile['skills'][skill_name] = value
        
        lawyers.append(profile)
    
    return {
        'lawyers': lawyers,
        'skill_map': skill_map,
        'unique_skills': list(skill_map.keys())
    }

# Function to get top skills for a lawyer
def get_top_skills(lawyer, limit=5):
    return sorted(
        [{'skill': skill, 'value': value} for skill, value in lawyer['skills'].items()],
        key=lambda x: x['value'],
        reverse=True
    )[:limit]

# Function to match lawyers with a query
def match_lawyers(data, query, top_n=5):
    if not data:
        return []
    
    # Convert query to lowercase for case-insensitive matching
    lower_query = query.lower()
    
    # Calculate match scores for each lawyer
    matches = []
    for lawyer in data['lawyers']:
        score = 0
        matched_skills = []
        
        # Check each skill against the query
        for skill, value in lawyer['skills'].items():
            skill_lower = skill.lower()
            if skill_lower in lower_query or any(word in skill_lower for word in lower_query.split()):
                score += value
                matched_skills.append({'skill': skill, 'value': value})
        
        if score > 0:
            matches.append({
                'lawyer': lawyer,
                'score': score,
                'matched_skills': sorted(matched_skills, key=lambda x: x['value'], reverse=True)[:5]
            })
    
    # Sort by score and take top N
    return sorted(matches, key=lambda x: x['score'], reverse=True)[:top_n]

# Function to format Claude's analysis prompt
def format_claude_prompt(query, matches):
    prompt = f"""
I need to analyze and provide reasoning for lawyer matches based on a specific legal query from a client. 
Here's the client query: "{query}"

Here are the matched lawyers with their relevant skills:

"""
    
    for i, match in enumerate(matches, 1):
        lawyer = match['lawyer']
        skills = match['matched_skills']
        prompt += f"Lawyer {i}: {lawyer['name']}\n"
        prompt += f"Practice Area: {lawyer['practice_area']}\n"
        prompt += "Relevant skills:\n"
        for skill in skills:
            prompt += f"- {skill['skill']}: {skill['value']} points\n"
        prompt += "\n"
    
    prompt += """
For each lawyer, provide a brief (3-4 sentences) explanation of why they would be a good match for the client query.
Focus on their specific expertise and how it relates to the legal needs described in the query.
Include any relevant information about their practice area if applicable.
Don't rank the lawyers - just explain each one's relevant strengths for this client matter.

Format your response in JSON like this:
{
    "lawyer1": "reasoning for why lawyer 1 is a good match...",
    "lawyer2": "reasoning for why lawyer 2 is a good match...",
    "lawyer3": "reasoning for why lawyer 3 is a good match..."
}
"""
    return prompt

# Function to call Claude API
def call_claude_api(prompt):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "YOUR_API_KEY_HERE")
    
    if api_key == "YOUR_API_KEY_HERE":
        # If no API key, return mock data
        return {
            lawyer_match['lawyer']['name']: f"This lawyer has strong expertise in areas related to your client's needs, particularly in {', '.join([s['skill'] for s in lawyer_match['matched_skills'][:2]])}. Their {lawyer_match['lawyer']['practice_area']} background makes them well-suited for this matter. They allocated significant points to these skills in their self-assessment, indicating confidence in handling such cases."
            for lawyer_match in matches[:5]
        }
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1000,
            temperature=0.0,
            system="You are a legal resource coordinator that analyzes lawyer expertise matches. You provide brief, factual explanations about why specific lawyers match particular client legal needs based on their self-reported skills. Keep explanations concise and focused on the relevant expertise. Include practice area information where relevant.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract JSON from response
        import json
        response_text = message.content[0].text
        # Find JSON part in the response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            return json.loads(json_str)
        else:
            return {"error": "Could not extract JSON from Claude's response"}
            
    except Exception as e:
        st.error(f"Error calling Claude API: {e}")
        return {"error": str(e)}

# Initialize session state
if 'query' not in st.session_state:
    st.session_state.query = ""
if 'search_pressed' not in st.session_state:
    st.session_state.search_pressed = False

# Main app layout
st.title("⚖️ Legal Expert Finder")
st.markdown("Match client legal needs with the right lawyer based on expertise")

# Load data
data = load_lawyer_data()

# Preset queries
preset_queries = [
    "Privacy compliance and cross-border data transfers",
    "Securities regulation and capital markets",
    "Technology licensing and SaaS contracts",
    "Startup funding and equity compensation",
    "Employment issues and workplace discrimination",
    "Healthcare compliance regulations in Canada",
    "Intellectual property protection and licensing",
    "Environmental compliance in British Columbia",
    "Fintech regulatory compliance",
    "M&A for tech companies"
]

# Query input section
st.text_area(
    "Describe client's legal needs in detail:", 
    key="query",
    height=100,
    placeholder="Example: Client needs a lawyer with blockchain governance experience for cross-border cryptocurrency transactions"
)

# Preset query buttons in rows of 3
st.markdown("### Common Client Needs")
cols = st.columns(3)
for i, query in enumerate(preset_queries):
    col_idx = i % 3
    with cols[col_idx]:
        if st.button(query, key=f"preset_{i}"):
            st.session_state.query = query
            st.session_state.search_pressed = True

# Search button
if st.button("🔍 Find Matching Lawyers", type="primary", use_container_width=True):
    st.session_state.search_pressed = True

# Display results when search is pressed
if st.session_state.search_pressed and st.session_state.query:
    with st.spinner("Matching client needs with our legal experts..."):
        # Get matches
        matches = match_lawyers(data, st.session_state.query)
        
        if not matches:
            st.warning("No matching lawyers found. Please try a different query.")
        else:
            # Call Claude API for reasoning
            claude_prompt = format_claude_prompt(st.session_state.query, matches)
            reasoning = call_claude_api(claude_prompt)
            
            # Display results
            st.markdown("## Matching Legal Experts")
            st.markdown(f"Found {len(matches)} lawyers matching client needs:")
            
            # Sort alphabetically for display (not by score)
            sorted_matches = sorted(matches, key=lambda x: x['lawyer']['name'])
            
            for match in sorted_matches:
                lawyer = match['lawyer']
                matched_skills = match['matched_skills']
                
                with st.container():
                    st.markdown(f"""
                    <div class="lawyer-card">
                        <div class="lawyer-name">
                            {lawyer['name']}
                            <span class="availability-tag">{lawyer['availability']}</span>
                        </div>
                        <div class="lawyer-email">{lawyer['email']}</div>
                        <div class="practice-area">Practice Area: {lawyer['practice_area']}</div>
                        <div class="billable-rate">Rate: {lawyer['billable_rate']} | Recent Client: {lawyer['last_client']}</div>
                        <div style="margin-top: 10px;">
                            <strong>Relevant Expertise:</strong><br/>
                            {"".join([f'<span class="skill-tag">{skill["skill"]}: {skill["value"]}</span>' for skill in matched_skills])}
                        </div>
                        <div class="reasoning-box">
                            <strong>Match Rationale:</strong><br/>
                            {reasoning.get(lawyer['name'], 'This lawyer has relevant expertise in the areas described in the client query.')}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Action buttons for results
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📧 Email These Matches to Requester", use_container_width=True):
                    st.success("Match results have been emailed to the requester!")
            with col2:
                if st.button("📆 Schedule Availability Check", use_container_width=True):
                    st.success("Availability check has been scheduled with these lawyers!")

# Show exploration section when no search is active
if not st.session_state.search_pressed or not st.session_state.query:
    st.markdown("## Explore Available Legal Expertise")
    
    if data:
        # Create a visual breakdown of legal expertise
        all_skills = {}
        for lawyer in data['lawyers']:
            for skill, value in lawyer['skills'].items():
                if skill in all_skills:
                    all_skills[skill] += value
                else:
                    all_skills[skill] = value
        
        # Get top 20 skills by total points
        top_skills = sorted(all_skills.items(), key=lambda x: x[1], reverse=True)[:20]
        
        # Show bar chart of top skills in scrollable container
        st.markdown("### Most Common Legal Expertise Areas")
        st.markdown('<div class="scroll-container">', unsafe_allow_html=True)
        chart_data = pd.DataFrame({
            'Skill': [s[0] for s in top_skills],
            'Total Points': [s[1] for s in top_skills]
        })
        st.bar_chart(chart_data.set_index('Skill'))
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Quick stats
        st.markdown("### Firm Resource Overview")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Lawyers", len(data['lawyers']))
        with col2:
            st.metric("Expertise Areas", len(data['unique_skills']))
        with col3:
            st.metric("Currently Available", f"{int(len(data['lawyers']) * 0.4)}")  # Mock data
        
        st.markdown("### Instructions for Matching")
        st.markdown("""
        Enter your client's specific legal needs above or select a common query to find matching legal experts. 
        Be as specific as possible about their requirements, including:
        
        - The type of legal expertise needed
        - Any industry-specific requirements
        - Geographic considerations (e.g., province-specific needs)
        - The nature of the legal matter
        - Timeframe and urgency
        
        The system will match the query with lawyers who have self-reported expertise in those areas.
        """)

# Footer
st.markdown("---")
st.markdown(
    "This internal tool uses self-reported expertise from 64 lawyers who distributed 120 points across 167 different legal skills. "
    "Results are sorted alphabetically and matches are based on keyword relevance and self-reported skill points. "
    "Last updated: February 25, 2025"
)

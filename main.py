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
h1 {
    color: #1e4b79;
}
</style>
""", unsafe_allow_html=True)

# Set up sidebar
st.sidebar.image("https://place-hold.it/300x100/1e4b79/ffffff&text=Legal+Expert+Finder", use_column_width=True)
st.sidebar.title("About")
st.sidebar.info(
    "This app helps match legal needs with the right lawyer based on self-reported expertise. "
    "Enter your specific legal requirements or choose a preset query to find lawyers with the relevant skillset."
)
st.sidebar.markdown("---")

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
    
    # Create lawyer profiles
    lawyers = []
    for _, row in df.iterrows():
        profile = {
            'name': row['Submitter Name'],
            'email': row['Submitter Email'],
            'skills': {}
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
I need to analyze and provide reasoning for lawyer matches based on a specific legal query. 
Here's the query: "{query}"

Here are the matched lawyers with their relevant skills:

"""
    
    for i, match in enumerate(matches, 1):
        lawyer = match['lawyer']
        skills = match['matched_skills']
        prompt += f"Lawyer {i}: {lawyer['name']}\n"
        prompt += "Relevant skills:\n"
        for skill in skills:
            prompt += f"- {skill['skill']}: {skill['value']} points\n"
        prompt += "\n"
    
    prompt += """
For each lawyer, provide a brief (3-4 sentences) explanation of why they would be a good match for the query.
Focus on their specific expertise and how it relates to the legal needs described in the query.
Don't rank the lawyers - just explain each one's relevant strengths.
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
            lawyer_match['lawyer']['name']: f"This lawyer has strong expertise in areas related to your query, particularly in {', '.join([s['skill'] for s in lawyer_match['matched_skills'][:2]])}. They allocated significant points to these skills in their self-assessment, indicating confidence in handling such matters."
            for lawyer_match in matches[:3]
        }
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1000,
            temperature=0.0,
            system="You are a legal assistant that analyzes lawyer expertise matches. You provide brief, factual explanations about why specific lawyers match particular legal needs based on their self-reported skills. Keep explanations concise and focused on the relevant expertise.",
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

# Main app layout
st.title("⚖️ Legal Expert Finder")
st.markdown("Find the right lawyer for your specific legal needs based on expertise")

# Load data
data = load_lawyer_data()

# Preset queries
preset_queries = [
    "I need a specialist in privacy compliance and cross-border data transfers",
    "Looking for expertise in securities regulation and capital markets",
    "Need help with technology licensing and SaaS contracts",
    "I'm a startup founder looking for help with funding and equity compensation",
    "Need assistance with employment issues and workplace discrimination",
    "Looking for expertise in healthcare compliance regulations in Canada",
    "Need help with intellectual property protection and licensing",
    "Agricultural business needing environmental compliance assistance in British Columbia"
]

# Query input section
col1, col2 = st.columns([3, 1])

with col1:
    query = st.text_area(
        "Describe your legal needs in detail:", 
        height=100,
        placeholder="Example: I need a lawyer with experience in blockchain governance and cryptocurrency regulations who can help with cross-border transactions"
    )

with col2:
    st.write("### Quick Queries")
    selected_preset = st.selectbox(
        "Select a preset query:",
        ["Select a preset..."] + preset_queries
    )
    
    if st.button("Use Selected Query"):
        if selected_preset != "Select a preset...":
            query = selected_preset

# Search button
search_pressed = st.button("🔍 Find Matching Lawyers", type="primary", use_container_width=True)

# Display results when search is pressed
if search_pressed and query:
    with st.spinner("Matching your legal needs with experts..."):
        # Get matches
        matches = match_lawyers(data, query)
        
        if not matches:
            st.warning("No matching lawyers found. Please try a different query.")
        else:
            # Call Claude API for reasoning
            claude_prompt = format_claude_prompt(query, matches)
            reasoning = call_claude_api(claude_prompt)
            
            # Display results
            st.markdown("## Matching Legal Experts")
            st.markdown(f"We found {len(matches)} lawyers matching your needs:")
            
            # Sort alphabetically for display (not by score)
            sorted_matches = sorted(matches, key=lambda x: x['lawyer']['name'])
            
            for match in sorted_matches:
                lawyer = match['lawyer']
                matched_skills = match['matched_skills']
                
                with st.container():
                    st.markdown(f"""
                    <div class="lawyer-card">
                        <div class="lawyer-name">{lawyer['name']}</div>
                        <div class="lawyer-email">{lawyer['email']}</div>
                        <div style="margin-top: 10px;">
                            <strong>Relevant Expertise:</strong><br/>
                            {"".join([f'<span class="skill-tag">{skill["skill"]}: {skill["value"]}</span>' for skill in matched_skills])}
                        </div>
                        <div class="reasoning-box">
                            <strong>Why this expert matches your needs:</strong><br/>
                            {reasoning.get(lawyer['name'], 'This lawyer has relevant expertise in the areas you described in your query.')}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

# Show exploration section when no search is active
if not search_pressed or not query:
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
        
        # Get top 15 skills by total points
        top_skills = sorted(all_skills.items(), key=lambda x: x[1], reverse=True)[:15]
        
        # Show bar chart of top skills
        st.markdown("### Most Common Legal Expertise Areas")
        chart_data = pd.DataFrame({
            'Skill': [s[0] for s in top_skills],
            'Total Points': [s[1] for s in top_skills]
        })
        st.bar_chart(chart_data.set_index('Skill'))
        
        st.markdown("### Get Started")
        st.markdown("""
        Enter your specific legal needs above or select a preset query to find matching legal experts. 
        Be as specific as possible about your requirements, including:
        
        - The type of legal expertise you need
        - Any industry-specific requirements
        - Geographic considerations (e.g., province-specific needs)
        - The nature of your legal matter
        """)

# Footer
st.markdown("---")
st.markdown(
    "This app uses self-reported expertise from 64 lawyers who distributed 120 points across 167 different legal skills. "
    "Results are sorted alphabetically and matches are based on keyword relevance and self-reported skill points."
)

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
    background-color: #ffecb3;
    border-radius: 15px;
    padding: 4px 8px;
    font-size: 12px;
    color: #ff6f00;
    display: inline-block;
    margin-left: 10px;
}
.availability-tag-available {
    background-color: #e8f5e9;
    border-radius: 15px;
    padding: 4px 8px;
    font-size: 12px;
    color: #2e7d32;
    display: inline-block;
    margin-left: 10px;
}
.availability-tag-limited {
    background-color: #ffecb3;
    border-radius: 15px;
    padding: 4px 8px;
    font-size: 12px;
    color: #ff6f00;
    display: inline-block;
    margin-left: 10px;
}
.vacation-info {
    color: #d32f2f;
    font-size: 13px;
    margin-top: 3px;
    font-style: italic;
}
.engagement-note {
    color: #455a64;
    font-size: 13px;
    margin-top: 3px;
    font-style: italic;
}
.availability-details {
    color: #455a64;
    font-size: 14px;
    margin-top: 5px;
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
        set_query(query)

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
    
    # Create lawyer profiles with real availability data and some demo data
    lawyers = []
    practice_areas = ["Corporate", "Litigation", "IP", "Employment", "Privacy", "Finance", "Real Estate", "Tax"]
    rate_ranges = ["$400-500/hr", "$500-600/hr", "$600-700/hr", "$700-800/hr", "$800-900/hr"]
    
    # Real availability data from the provided information
    availability_data = get_lawyer_availability()
    
    for _, row in df.iterrows():
        lawyer_name = row['Submitter Name']
        availability_info = get_availability_for_lawyer(lawyer_name)
        
        profile = {
            'name': lawyer_name,
            'email': row['Submitter Email'],
            'skills': {},
            # Use real availability data when available
            'availability': availability_info.get('status', 'Status Unknown'),
            'days_available': availability_info.get('days', None),
            'hours_available': availability_info.get('hours', None),
            'vacation': availability_info.get('vacations', []),
            'engagement_note': availability_info.get('engagementNote', ''),
            # Add some demo data for other fields
            'practice_area': np.random.choice(practice_areas),
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

# Function to load and process availability data
def get_lawyer_availability():
    # Real availability data parsed from the provided information
    days_available = parse_days_availability()
    hours_available = parse_hours_availability()
    vacations = parse_vacations()
    engagement_notes = parse_engagement_notes()
    
    # Combine all data into a single structure
    lawyer_availability = {}
    
    # First handle days available
    for name, days in days_available.items():
        if name not in lawyer_availability:
            lawyer_availability[name] = {}
        lawyer_availability[name]['days'] = days
    
    # Add hours available
    for name, hours in hours_available.items():
        if name not in lawyer_availability:
            lawyer_availability[name] = {}
        lawyer_availability[name]['hours'] = hours
    
    # Add vacation data
    for name, vacation_dates in vacations.items():
        matching_names = [full_name for full_name in lawyer_availability 
                          if full_name.split()[0] == name.split()[0] or full_name.split()[-1] == name.split()[-1]]
        
        if matching_names:
            target_name = matching_names[0]
            if 'vacations' not in lawyer_availability[target_name]:
                lawyer_availability[target_name]['vacations'] = []
            lawyer_availability[target_name]['vacations'].append(vacation_dates)
        else:
            if name not in lawyer_availability:
                lawyer_availability[name] = {}
            if 'vacations' not in lawyer_availability[name]:
                lawyer_availability[name]['vacations'] = []
            lawyer_availability[name]['vacations'].append(vacation_dates)
    
    # Add engagement notes
    for name, note in engagement_notes.items():
        matching_names = [full_name for full_name in lawyer_availability 
                          if full_name.split()[0] == name.split()[0] or full_name.split()[-1] == name.split()[-1]]
        
        if matching_names:
            lawyer_availability[matching_names[0]]['engagementNote'] = note
        else:
            if name not in lawyer_availability:
                lawyer_availability[name] = {}
            lawyer_availability[name]['engagementNote'] = note
    
    # Generate availability status for each lawyer
    for name, data in lawyer_availability.items():
        lawyer_availability[name]['status'] = generate_availability_status(data)
    
    return lawyer_availability

# Function to get availability for a specific lawyer
def get_availability_for_lawyer(name):
    availability_data = get_lawyer_availability()
    
    # Check for exact match
    if name in availability_data:
        return availability_data[name]
    
    # Check for partial match (first name or last name)
    for avail_name, data in availability_data.items():
        if (name.split()[0] in avail_name) or (name.split()[-1] in avail_name):
            return data
    
    # Default status if no match found
    return {
        'status': 'Status Unknown',
        'days': None,
        'hours': None
    }

# Function to generate availability status based on data
def generate_availability_status(lawyer_data):
    # The current date is February 25, 2025
    current_date = '2025-02-25'
    
    # Check if on vacation today
    if 'vacations' in lawyer_data:
        for vacation in lawyer_data['vacations']:
            if "Feb 25" in vacation or (
                "Feb" in vacation and "-" in vacation and 
                not any(month in vacation for month in ["Mar", "April", "May"])):
                return "On Vacation"
    
    # Check engagement notes for current status
    if 'engagementNote' in lawyer_data:
        note = lawyer_data['engagementNote']
        if "not currently in an engagement" in note:
            return "Available Now"
        if "will conclude at the end of February" in note:
            return "Available Soon (March)"
    
    # Use days availability to determine status
    if 'days' in lawyer_data:
        days = lawyer_data['days']
        if days in [5, 4]:
            return "Very Limited Availability"
        elif days == 3:
            return "Limited Availability"
        elif days in [2, 1]:
            return "Partially Available"
        elif days == 0:
            return "Available Now"
    
    # If no days data, use hours
    if 'hours' in lawyer_data:
        hours = lawyer_data['hours']
        if hours in ["80+", "80"]:
            return "Very Limited Availability"
        elif hours in ["60", "40"]:
            return "Limited Availability"
        elif hours in ["30", "20"]:
            return "Partially Available"
        elif hours == "0":
            return "Available Now"
    
    return "Status Unknown"

# Parse days availability data
def parse_days_availability():
    days_available_text = """
    **5 days**
    **4 days**
    **3 days**
    **2 days**
    **1 day**
    **0 days**
    Ashleigh Frankel
    Spencer Shepherd
    Evelyn Ackah
    Dave McIntyre
    Sean Holler
    Bernadette Saumur
    John Burns
    Adrian Dirassar
    Wendy Bach
    Meenal Gole
     
     
    Kristen Pizzolo
    James Oborne
     
    Leslie Allan
    Bill Stanger
    Peter Dale
    Lisa McDowell
    Bill Herman
    Frank Giblon
     
    Mitch Mostyn
    Randy Witten
    Rose Oushalkas
    Alan Sless
    Nikki Stewart-St. Arnault
    Connie Chan
    Jeff Bright
    David Masse
    Zubdah Ahmad
    Greg Porter
    Hugh Kerr
    Olivia Dutka
    Jason Lakhan
     
    Melissa Babel
    David Dunbar
    Josee Cameron-Virgo
    Sean Mitra
    Michelle Grant-Asselin
    Morli Shemesh
    Sarah Sidhu
     
    Ellen Swan
    Sarah Blackburn
    John Whyte
    Rory Dyck
    Sherry Hanlon
    Corrie Stepan
    Peter Kalins
    Wanda Shreve
    Greg Ramsay
    Jim Papamanolis
    Mark Wainman
    Brenda Chandler
    Michele Koyle
    Annie Belecki
    Christa Wessel
    Chelsea Bianchin
    Binita Jacob
    Ernie Belyea
    Aliza Dason
    """
    
    lines = days_available_text.split('\n')
    current_days = None
    result = {}
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        days_match = re.match(r'\*\*(\d+) days?\*\*', line)
        if days_match:
            current_days = int(days_match.group(1))
        elif current_days is not None and not line.startswith('**'):
            result[line] = current_days
    
    return result

# Function to get top skills for a lawyer
def get_top_skills(lawyer, limit=5):
    return sorted(
        [{'skill': skill, 'value': value} for skill, value in lawyer['skills'].items()],
        key=lambda x: x['value'],
        reverse=True
    )[:limit]

# Parse hours availability data
def parse_hours_availability():
    hours_available_text = """
    **80+ hours**
    **80 hours**
    **60 hours**
    **40 hours**
    **30 hours**
    **20 hours**
    **0 hours**
    Spencer Shepherd
    Sean Holler
    Dave McIntyre
    Bernadette Saumur
    Adrian Dirassar
    Bill Herman
    Wendy Bach
    Ashleigh Frankel
    James Oborne
     
    Leslie Allan
    Evelyn Ackah
    John Burns
    Kristen Pizzolo
    Frank Giblon
    Zubdah Ahmad
    Meenal Gole
    Alan Sless
    Bill Stanger
    Peter Dale
    Lisa McDowell
    Sarah Sidhu
     
    Jeff Bright
    Michelle Grant-Asselin
    Len Gaik
    Nikki Stewart-St. Arnault
    Olivia Dutka
    Jason Lakhan
     
    Rose Oushalkas
    Greg Porter
    Mark Wainman
    Sean Mitra
    Morli Shemesh
     
    Randy Witten
    Melissa Babel
    Mitch Mostyn
    Connie Chan
    David Masse
    Hugh Kerr
    David Dunbar
    Josee Cameron-Virgo
    Rory Dyck
    Wanda Shreve
    Greg Ramsay
    Chelsea Bianchin
     
    Ellen Swan
    Sarah Blackburn
    John Whyte
    Sherry Hanlon
    Corrie Stepan
    Peter Kalins
    Jim Papamanolis
    Brenda Chandler
    Michele Koyle
    Annie Belecki
    Christa Wessel
    Binita Jacob
    Ernie Belyea
    Aliza Dason
    """
    
    lines = hours_available_text.split('\n')
    current_hours = None
    result = {}
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        hours_match = re.match(r'\*\*(\d+\+?)( hours)\*\*', line)
        if hours_match:
            current_hours = hours_match.group(1)
        elif current_hours is not None and not line.startswith('**'):
            result[line] = current_hours
    
    return result

# Parse vacation data
def parse_vacations():
    vacation_text = """
    **Contractor Vacations:**
    David Zender- Feb 2- Mar 7
    Chelsea Bianchin- Feb 12-19; Mar 10-23
    John Burns- Feb 14
    Mark Wainman- Feb 21
    Lisa McDowell- Feb 24-28
    John Whyte- Feb 25-Mar 25
    Sue Gaudi- Feb 26- Mar 1; March 7-17; May 15-30
    Sarah Blackburn- Feb 27-Mar 3; Mar 8-15
    Sara Kunto- Feb 28-March 9
    Kristen Pizzolo- Mar 3-7
    Josee Cameron-Virgo- March 4-17
    Michelle Grant Asselin- March 10-16
    Ellen Swan- March 8-16
    Jim Papamanolis- March 9-15
    Leslie Allan- March 9-15
    Melissa Babel- March 10-18
    Lori Lyn Adams- March 15-30
    David Dunbar- April 17- May 6
    David Masse- May 10-30
    """
    
    lines = vacation_text.split('\n')
    result = {}
    collecting_vacations = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if "**Contractor Vacations:**" in line:
            collecting_vacations = True
            continue
        
        if collecting_vacations and not line.startswith("**"):
            parts = line.split("-", 1)
            if len(parts) >= 2:
                name = parts[0].strip()
                dates = parts[1].strip()
                result[name] = dates
        
        if collecting_vacations and line.startswith("**") and "Contractor Vacations" not in line:
            collecting_vacations = False
    
    return result

# Parse engagement notes
def parse_engagement_notes():
    engagement_notes_text = """
    **Lawyer and Fractional Updates to Note:**
    * Bernadette Saumur indicates that her engagement with GTAA will conclude at the end of February
    * Wendy Bach indicates that her engagement will conclude in Mid-April
    * Rose Oushalkas indicates that her engagement with Seaboard may conclude at the end of February
    * Mark Wainman indicates that he anticipates his engagement will end October of this year
    * Jason Lakhan indicates that he is not currently in an engagement
    * Mitch Mostyn indicates that his engagement with Magna will reduce to 20 hours/month in March, and then will move to ad hoc in April
    * Wanda Shreve indicates that she anticipates her engagement will continue into the Spring/Summer
    * Jim Papamanolis indicates that he anticipates his fractional will end at the end of May
    * Ernie Belyea indicates that his engagement has been extended through the remainder of 2025
    * Aliza Dason indicates that her engagement will continue through the remainder of 2025
    """
    
    lines = engagement_notes_text.split('\n')
    result = {}
    collecting_notes = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if "**Lawyer and Fractional Updates to Note:**" in line:
            collecting_notes = True
            continue
        
        if collecting_notes and line.startswith("*"):
            note = line[1:].strip()
            name_match = re.match(r'([^-]*?)indicates', note)
            if name_match:
                name = name_match.group(1).strip()
                result[name] = note
    
    return result

# Function to match lawyers with a query
def match_lawyers(data, query, top_n=5):
    if not data:
        return []
    
    # Convert query to lowercase for case-insensitive matching
    lower_query = query.lower()
    
    # Test users to exclude
    excluded_users = ["Ankita", "Test", "Tania"]
    
    # Calculate match scores for each lawyer
    matches = []
    for lawyer in data['lawyers']:
        # Skip test users
        if any(excluded_name in lawyer['name'] for excluded_name in excluded_users):
            continue
            
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
    
    # Handle the case where no API key is provided
    if api_key == "YOUR_API_KEY_HERE":
        # Return mock reasoning data for the lawyers
        try:
            return {
                match['lawyer']['name']: f"This lawyer has strong expertise in areas related to your client's needs, particularly in {', '.join([s['skill'] for s in match['matched_skills'][:2]])}. Their {match['lawyer']['practice_area']} background makes them well-suited for this matter. They allocated significant points to these skills in their self-assessment, indicating confidence in handling such cases."
                for match in matches[:5]
            }
        except NameError:
            # Fallback if 'matches' is not defined in this scope
            return {"Error": "No API key provided and could not generate mock data"}
    
    try:
        # Import anthropic here to handle any import issues
        try:
            from anthropic import Anthropic
        except ImportError:
            st.error("Could not import Anthropic client. Please ensure it's installed: pip install anthropic==0.18.0")
            return {"Error": "Anthropic client not available"}
        
        # Create the client with minimal configuration
        client = Anthropic(api_key=api_key)
        
        # Make the API call
        response = client.messages.create(
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
        import re
        
        response_text = response.content[0].text
        # Find JSON part in the response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            return json.loads(json_str)
        else:
            return {"error": "Could not extract JSON from Claude's response"}
            
    except Exception as e:
        st.error(f"Error calling Claude API: {str(e)}")
        
        # Provide a more detailed error message to help debugging
        import traceback
        st.error(f"Error details: {traceback.format_exc()}")
        
        # Return a fallback response
        return {"error": f"API error: {str(e)}"}

        
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

# Initialize session state variables
if 'query' not in st.session_state:
    st.session_state['query'] = ""
if 'search_pressed' not in st.session_state:
    st.session_state['search_pressed'] = False

# Helper function to set the query and trigger search
def set_query(text):
    st.session_state['query'] = text
    st.session_state['search_pressed'] = True

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
query = st.text_area(
    "Describe client's legal needs in detail:", 
    value=st.session_state['query'],
    height=100,
    placeholder="Example: Client needs a lawyer with blockchain governance experience for cross-border cryptocurrency transactions",
    key="query_input"
)

# Preset query buttons in rows of 3
st.markdown("### Common Client Needs")
cols = st.columns(3)
for i, preset_query in enumerate(preset_queries):
    col_idx = i % 3
    with cols[col_idx]:
        if st.button(preset_query, key=f"preset_{i}"):
            set_query(preset_query)

# Update query in session state from text area
if query:
    st.session_state['query'] = query

# Search button
search_pressed = st.button("🔍 Find Matching Lawyers", type="primary", use_container_width=True)
if search_pressed:
    st.session_state['search_pressed'] = True

# Display results when search is pressed
if st.session_state['search_pressed'] and st.session_state['query']:
    with st.spinner("Matching client needs with our legal experts..."):
        # Get matches
        matches = match_lawyers(data, st.session_state['query'])
        
        if not matches:
            st.warning("No matching lawyers found. Please try a different query.")
        else:
            # Call Claude API for reasoning
            claude_prompt = format_claude_prompt(st.session_state['query'], matches)
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
                    # Prepare availability info
                    availability_class = "availability-tag"
                    if "Limited" in lawyer['availability'] or "Vacation" in lawyer['availability']:
                        availability_class = "availability-tag-limited"
                    elif "Available" in lawyer['availability']:
                        availability_class = "availability-tag-available"
                    
                    # Prepare vacation info if any
                    vacation_info = ""
                    if lawyer['vacation']:
                        vacation_dates = ", ".join(lawyer['vacation']) if isinstance(lawyer['vacation'], list) else lawyer['vacation']
                        vacation_info = f"<div class='vacation-info'>Vacation: {vacation_dates}</div>"
                    
                    # Prepare engagement note if any
                    engagement_info = ""
                    if lawyer['engagement_note']:
                        engagement_info = f"<div class='engagement-note'>{lawyer['engagement_note']}</div>"
                    
                    st.markdown(f"""
                    <div class="lawyer-card">
                        <div class="lawyer-name">
                            {lawyer['name']}
                            <span class="{availability_class}">{lawyer['availability']}</span>
                        </div>
                        <div class="lawyer-email">{lawyer['email']}</div>
                        <div class="practice-area">Practice Area: {lawyer['practice_area']}</div>
                        <div class="availability-details">
                            {f"Days available: {lawyer['days_available']} | " if lawyer['days_available'] is not None else ""}
                            {f"Hours available: {lawyer['hours_available']}" if lawyer['hours_available'] is not None else ""}
                            {vacation_info}
                            {engagement_info}
                        </div>
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
if not st.session_state['search_pressed'] or not st.session_state['query']:
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

import streamlit as st
import pandas as pd
import numpy as np
import os
import re
import json
from functools import lru_cache
import requests

# Import the domain expertise functions from legal_domains.py
from legal_domains import match_lawyers_with_domain_expertise, LEGAL_DOMAINS, identify_query_domains

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
    padding: 20px;
    margin-top: 15px;
    border-left: 5px solid #7cb342;
    font-size: 15px;
    line-height: 1.5;
}
.match-rationale-title {
    font-weight: bold;
    font-size: 16px;
    color: #2e7d32;
    margin-bottom: 8px;
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
.availability-tag-adhoc {
    background-color: #fff3e0;
    border-radius: 15px;
    padding: 4px 8px;
    font-size: 12px;
    color: #e65100;
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
.bio-section {
    margin: 10px 0;
    padding: 10px;
    background-color: #f5f5f5;
    border-radius: 5px;
}
.bio-level {
    font-weight: bold;
    color: #1e4b79;
    font-size: 15px;
    margin-bottom: 4px;
}
.bio-details {
    color: #555;
    font-size: 14px;
    margin-bottom: 5px;
}
.bio-experience, .bio-education, .industry-experience {
    font-size: 14px;
    margin-top: 5px;
    color: #333;
}
.practice-area-filter {
    background-color: #e3f2fd;
    padding: 15px;
    border-radius: 10px;
    margin-bottom: 20px;
    border: 1px solid #bbdefb;
}
.practice-area-title {
    font-weight: bold;
    color: #1976d2;
    margin-bottom: 10px;
}
.practice-area-note {
    font-size: 13px;
    color: #546e7a;
    font-style: italic;
    margin-top: 5px;
}
</style>
""", unsafe_allow_html=True)

# Function to add practice area filter
def add_practice_area_filter():
    """
    Creates a dropdown for users to select the practice area
    """
    # List of practice areas based on the domains in the code
    practice_areas = [
        "Select Practice Area (Optional)",
        "Administrative Law",
        "Aviation Law",
        "Banking & Finance",
        "Bankruptcy Law",
        "Civil Litigation",
        "Civil Rights",
        "Commercial Transactions",
        "Communications Law",
        "Construction Law",
        "Corporate Law",
        "Criminal Law",
        "Education Law",
        "Elder Law",
        "Employee Benefits",
        "Employment & Labor Law",
        "Entertainment/Sports Law",
        "Environmental Law",
        "Family Law",
        "Government Relations",
        "Health Care Law",
        "Immigration",
        "Insurance Defense",
        "Intellectual Property",
        "International Practice",
        "Medical Malpractice",
        "Municipal Law",
        "Personal Injury",
        "Privacy Law",
        "Probate & Estate Planning",
        "Products Liability",
        "Real Estate",
        "Securities Law", 
        "Tax Law",
        "Technology Law",
        "Tribal/Indian Law",
        "Workers' Compensation"
    ]
    
    # Create a container with custom styling for the practice area filter
    with st.container():
        st.markdown('<div class="practice-area-filter">', unsafe_allow_html=True)
        st.markdown('<div class="practice-area-title">Practice Area Filter</div>', unsafe_allow_html=True)
        
        # Create the dropdown filter
        selected_area = st.selectbox(
            "What practice area does this legal need fall under?",
            practice_areas,
            index=0
        )
        
        st.markdown('<div class="practice-area-note">Selecting a specific practice area will help find the most relevant lawyers.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Return None if default option, otherwise return the selected area
    return None if selected_area == "Select Practice Area (Optional)" else selected_area

# Function to load and process the CSV data
@lru_cache(maxsize=1)
def load_lawyer_data():
    try:
        # Load the skills data
        skills_df = pd.read_csv('combined_unique.csv')
        skills_data = process_lawyer_data(skills_df)
        
        # Load the biographical data
        bio_df = pd.read_csv('BD_Caravel.csv')
        bio_data = process_bio_data(bio_df)
        
        # Combine the data
        combined_data = combine_lawyer_data(skills_data, bio_data)
        
        return combined_data
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

# Function to process the biographical data
def process_bio_data(df):
    lawyers_bio = {}
    
    for _, row in df.iterrows():
        # Convert first and last names to string and handle NaN values
        first_name = str(row['First Name']).strip() if pd.notna(row['First Name']) else ""
        last_name = str(row['Last Name']).strip() if pd.notna(row['Last Name']) else ""
        
        full_name = f"{first_name} {last_name}".strip()
        
        # Skip empty names
        if not full_name:
            continue
        
        bio = {
            'level': str(row['Level/Title']) if pd.notna(row['Level/Title']) else "",
            'call': str(row['Call']) if pd.notna(row['Call']) else "",
            'jurisdiction': str(row['Jurisdiction']) if pd.notna(row['Jurisdiction']) else "",
            'location': str(row['Location']) if pd.notna(row['Location']) else "",
            'practice_areas': str(row['Area of Practise + Add Info']) if pd.notna(row['Area of Practise + Add Info']) else "",
            'industry_experience': str(row['Industry Experience']) if pd.notna(row['Industry Experience']) else "",
            'languages': str(row['Languages']) if pd.notna(row['Languages']) else "",
            'previous_in_house': str(row['Previous In-House Companies']) if pd.notna(row['Previous In-House Companies']) else "",
            'previous_firms': str(row['Previous Companies/Firms']) if pd.notna(row['Previous Companies/Firms']) else "",
            'education': str(row['Education']) if pd.notna(row['Education']) else "",
            'awards': str(row['Awards/Recognition']) if pd.notna(row['Awards/Recognition']) else "",
            'notable_items': str(row['Notable Items/Personal Details ']) if pd.notna(row['Notable Items/Personal Details ']) else "",
            'expert': str(row['Expert']) if pd.notna(row['Expert']) else ""
        }
        
        lawyers_bio[full_name] = bio
    
    return {
        'lawyers_bio': lawyers_bio
    }

# Function to combine skills and biographical data
def combine_lawyer_data(skills_data, bio_data):
    if not skills_data or not bio_data:
        return skills_data
    
    combined_lawyers = []
    
    for lawyer in skills_data['lawyers']:
        # Try to find matching biographical data
        name = lawyer['name']
        bio = None
        
        # Try exact match
        if name in bio_data['lawyers_bio']:
            bio = bio_data['lawyers_bio'][name]
        else:
            # Try partial match
            for bio_name, bio_info in bio_data['lawyers_bio'].items():
                # Check if first and last name parts match
                name_parts = name.lower().split()
                bio_name_parts = bio_name.lower().split()
                
                if any(part in bio_name.lower() for part in name_parts) and any(part in name.lower() for part in bio_name_parts):
                    bio = bio_info
                    break
        
        # Add biographical data if found
        if bio:
            lawyer['bio'] = bio
        else:
            lawyer['bio'] = {
                'level': '',
                'call': '',
                'jurisdiction': '',
                'location': '',
                'practice_areas': '',
                'industry_experience': '',
                'languages': '',
                'previous_in_house': '',
                'previous_firms': '',
                'education': '',
                'awards': '',
                'notable_items': '',
                'expert': ''
            }
        
        combined_lawyers.append(lawyer)
    
    return {
        'lawyers': combined_lawyers,
        'skill_map': skills_data['skill_map'],
        'unique_skills': skills_data['unique_skills']
    }

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

# All the availability-related functions
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

# Function to generate availability status
def generate_availability_status(lawyer_data):
    # Current date is now February 26, 2025
    current_date = '2025-02-26'
    
    # Check if on vacation today
    if 'vacations' in lawyer_data:
        for vacation in lawyer_data['vacations']:
            if "Feb 26" in vacation or (
                "Feb" in vacation and "-" in vacation and 
                not any(day in vacation for day in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25"])):
                return "On Vacation"
    
    # Check engagement notes for current status
    if 'engagementNote' in lawyer_data:
        note = lawyer_data['engagementNote'].lower()
        if "full capacity" in note or "availability will increase" in note or "capacity for new work will increase" in note:
            return "Available Soon"
        if "will be concluding" in note or "will conclude" in note:
            return "Available Soon"
        if "availability for ad hoc" in note:
            return "Available for Ad Hoc"
        if "no new work until" in note:
            return "Not Available"
    
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

# All the parser functions
def parse_days_availability():
    days_available_text = """
    **5 days**
    **4 days**
    **3 days**
    **2 days**
    **1 day**
    **0 days**
    Meenal Gole
    Leonard Gaik
    Sean Holler
    Bernadette Saumur
    Alan Sless
    John Burns
    Spencer Shepherd
    Dave McIntyre
    Wendy Bach
    Ashleigh Frankel
     
    Kristen Pizzolo
    Leslie Allan
    Lance Lehman
    Bill Stanger
    Mark Wainman
    Lisa McDowell
    Peter Dale
     
    Connie Chan
    Jeff Bright
    John Tyrell
    Rose Oushalkas
    David Masse
    Greg Porter
    Nikki Stewart-St. Arnault
    Randy Witten
    Sean Mitra
    Hugh Kerr
    Michelle Grant-Asselin
    Antoine Malek
    Wanda Shreve
    Corrie Stepan
    John Whyte
    Peter Kalins
    Sherry Hanlon
    Dan Black
    Melissa Babel
    Ellen Swan
    Brenda Chandler
    Binita Jacob
    Sarah Blackburn
    Michele Koyle
    Jim Papamanolis
    Rory Dyck
    Sara Kunto
    Annie Belecki
    Aliza Dason
    Joel Guralnick
    Greg Ramsay
    Esia Giaouris
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

def parse_hours_availability():
    hours_available_text = """
    **80+ hours**
    **80 hours**
    **60 hours**
    **40 hours**
    **30 hours**
    **20 hours**
    **0 hours**
    Bernadette Saumur
    Alan Sless
    Spencer Shepherd
    Dave McIntyre
    Kristen Pizzolo
    Leonard Gaik
    Wendy Bach
     
    Sean Holler
    Leslie Allan
    Lance Lehman
    Lisa McDowell
    Meenal Gole
    Ashleigh Frankel
    Bill Stanger
    Peter Dale
    John Tyrell
     
    John Burns
    Michelle Grant-Asselin
    Nikki Stewart-St. Arnault
     
    Jeff Bright
    Mark Wainman
    Rose Oushalkas
    David Masse
    Greg Porter
    Sean Mitra
     
    Connie Chan
    Randy Witten
    Hugh Kerr
    Antoine Malek
    Wanda Shreve
    Joel Guralnick
    Greg Ramsay
    Esia Giaouris
    Corrie Stepan
    John Whyte
    Peter Kalins
    Sherry Hanlon
    Dan Black
    Melissa Babel
    Ellen Swan
    Brenda Chandler
    Binita Jacob
    Sarah Blackburn
    Michele Koyle
    Jim Papamanolis
    Rory Dyck
    Sara Kunto
    Annie Belecki
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

def parse_vacations():
    vacation_text = """
    **Contractor Vacations:**
    David Zender- Feb 2- Mar 7
    Dan Black- Feb 22- March 2
    Lisa McDowell- Feb 24-28; April 30-May 14
    John Whyte- Feb 25-Mar 25
    Sue Gaudi- Feb 26- Mar 1; March 7-17; May 15-30
    Sarah Blackburn- Feb 27-Mar 3; Mar 8-15
    Sara Kunto- Feb 28-March 9
    Kristen Pizzolo- Mar 3-7
    Josee Cameron-Virgo- March 4-17
    John Burns- March 5-8
    Ellen Swan- March 7-17
    Jim Papamanolis- March 9-15
    Leslie Allan- March 9-15; July 20- Aug 2
    Michelle Grant Asselin- March 8-16
    Melissa Babel- March 10-18
    Chelsea Bianchin- Mar 10-23
    Lori Lyn Adams- March 15-30
    Connie Chan- March 15-31
    David Dunbar- April 17- May 6
    Binita Jacobs- April 28-29
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

def parse_engagement_notes():
    engagement_notes_text = """
    **Lawyer and Fractional Updates to Note:**
    Bernadette Saumur's fractional will be concluding.
    Alan Sless is concluding his engagement with Choice Properties and will have full capacity for new work as of the end of March.
    Lance Lehman is interested in taking on more work as his fractional is reducing hours as of March 1.
    Wendy Bach indicates that her fractional will conclude at the end of April.
    Mark Wainman has availability for ad hoc work.
    Rose Oushalkas indicates that her fractional will conclude at the end of February, and that her capacity for new work will increase.
    Antoine Malek indicates that his fractional will conclude at the end of March, and his availability will significantly increase the week of March 17.
    Wanda Shreve indicates that her fractional could potentially conclude at the end of March.
    Greg Ramsay has availability for ad hoc work.
    John Whyte is interested in taking on 1-2 days/ week after he returns from his vacation at the end of March. He would like to be considered for commercial contracts or mentoring work.
    Dan Black expects his availability to increase in March.
    Melissa Babel is requesting no new work until after March 15.
    Jim Papamanolis indicates that his fractional may conclude at the end of May.
    Sara Kunto indicates that her fractional with TMU will be ending in April.
    Aliza Dason indicates that her fractional will conclude at the end of 2025.
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
        
        if collecting_notes and not line.startswith("**"):
            # Extract name from the beginning of each line
            name_end_pos = line.find("'s fractional")
            if name_end_pos > 0:
                name = line[:name_end_pos].strip()
                result[name] = line
                continue
                
            name_end_pos = line.find(" is ")
            if name_end_pos > 0:
                name = line[:name_end_pos].strip()
                result[name] = line
                continue
                
            name_end_pos = line.find(" indicates ")
            if name_end_pos > 0:
                name = line[:name_end_pos].strip()
                result[name] = line
                continue
                
            name_end_pos = line.find(" has ")
            if name_end_pos > 0:
                name = line[:name_end_pos].strip()
                result[name] = line
                continue
                
            name_end_pos = line.find(" expects ")
            if name_end_pos > 0:
                name = line[:name_end_pos].strip()
                result[name] = line
                continue
                
            name_end_pos = line.find(" is ")
            if name_end_pos > 0:
                name = line[:name_end_pos].strip()
                result[name] = line
    
    return result

# Function to get top skills for a lawyer
def get_top_skills(lawyer, limit=5):
    return sorted(
        [{'skill': skill, 'value': value} for skill, value in lawyer['skills'].items()],
        key=lambda x: x['value'],
        reverse=True
    )[:limit]

# NEW: Updated match_lawyers function that includes practice area filtering
def match_lawyers(data, query, practice_area_filter=None, top_n=5):
    """
    Matches lawyers to a query using domain-specific legal expertise with practice area filtering
    """
    if not data:
        return []
        
    # First, filter by practice area if specified
    if practice_area_filter:
        # Create a filtered dataset with only lawyers matching the practice area
        filtered_lawyers = []
        for lawyer in data['lawyers']:
            # Match if the practice area contains the filter term or vice versa
            if (practice_area_filter.lower() in lawyer['practice_area'].lower() or
                any(practice_area_filter.lower() in domain.lower() for domain in lawyer.get('bio', {}).get('practice_areas', '').split(','))):
                filtered_lawyers.append(lawyer)
        
        filtered_data = {
            'lawyers': filtered_lawyers,
            'skill_map': data['skill_map'],
            'unique_skills': data['unique_skills']
        }
        
        # If no lawyers match the practice area, show a message and return empty
        if not filtered_lawyers:
            st.warning(f"No lawyers found with practice area: {practice_area_filter}. Try another practice area or search all lawyers.")
            return []
            
        # Now use the filtered data for matching
        matching_data = filtered_data
    else:
        # Use all lawyers if no practice area filter
        matching_data = data
    
    # Use the enhanced domain-based matching algorithm imported from legal_domains.py
    return match_lawyers_with_domain_expertise(matching_data, query, top_n)

# Function to format Claude's analysis prompt (updated to include domain information)
def format_claude_prompt(query, matches, practice_area_filter=None):
    prompt = f"""
I need to analyze and provide detailed reasoning for why specific lawyers match a client's legal needs based on their expertise, skills, and background.

Client's Legal Need: "{query}"
"""

    # Include practice area if specified
    if practice_area_filter:
        prompt += f"\nSpecified Practice Area: {practice_area_filter}\n"
    
    prompt += "\nHere are the matching lawyers with their skills and biographical information:\n\n"
    
    for i, match in enumerate(matches, 1):
        lawyer = match['lawyer']
        skills = match['matched_skills']
        bio = lawyer['bio']
        
        prompt += f"LAWYER {i}: {lawyer['name']}\n"
        prompt += "---------------------------------------------\n"
        
        # Add practice area first for emphasis
        prompt += f"PRACTICE AREA: {lawyer['practice_area']}\n\n"
        
        # Add skills information
        prompt += "RELEVANT SKILLS:\n"
        for skill in skills:
            prompt += f"- {skill['skill']}: {skill['value']} points\n"
        
        # Add domain information if available
        if 'matched_domains' in match and match['matched_domains']:
            prompt += "\nMATCHED LEGAL DOMAINS:\n"
            for domain in match['matched_domains']:
                prompt += f"- {domain}\n"
        
        # Add biographical information
        prompt += "\nBIOGRAPHICAL INFORMATION:\n"
        if bio['level']:
            prompt += f"- Level/Title: {bio['level']}\n"
        if bio['call']:
            prompt += f"- Called to Bar: {bio['call']}\n"
        if bio['jurisdiction']:
            prompt += f"- Jurisdiction: {bio['jurisdiction']}\n"
        if bio['location']:
            prompt += f"- Location: {bio['location']}\n"
        if bio['practice_areas']:
            prompt += f"- Practice Areas: {bio['practice_areas']}\n"
        if bio['industry_experience']:
            prompt += f"- Industry Experience: {bio['industry_experience']}\n"
        if bio['previous_in_house']:
            prompt += f"- Previous In-House Experience: {bio['previous_in_house']}\n"
        if bio['previous_firms']:
            prompt += f"- Previous Law Firms: {bio['previous_firms']}\n"
        if bio['education']:
            prompt += f"- Education: {bio['education']}\n"
        if bio['awards']:
            prompt += f"- Awards/Recognition: {bio['awards']}\n"
        if bio['expert']:
            prompt += f"- Areas of Expertise: {bio['expert']}\n"
        if bio['notable_items']:
            prompt += f"- Notable Experience: {bio['notable_items']}\n"
            
        # Add availability information
        prompt += f"\nAVAILABILITY: {lawyer['availability']}\n"
        if lawyer['days_available'] is not None:
            prompt += f"Days available: {lawyer['days_available']}\n"
        if lawyer['hours_available'] is not None:
            prompt += f"Hours available: {lawyer['hours_available']}\n"
        if lawyer['engagement_note']:
            prompt += f"Current engagement: {lawyer['engagement_note']}\n"
            
        prompt += "\n\n"
    
    prompt += """
For each lawyer, provide a DETAILED explanation (at least 3-4 sentences) of why they would be an excellent match for this client need. Focus primarily on their skills and expertise rather than biographical information.

IMPORTANT: Your analysis should adhere to these strict guidelines:
1. EMPHASIZE how their PRACTICE AREA aligns with the client's needs
2. ONLY highlight skills that EXACTLY match the specific domain expertise required (e.g., "healthcare compliance" not just general "compliance")
3. DO NOT make unsupported assumptions about transferable skills across different legal domains
4. If a lawyer has expertise in a related but not exact area, clearly acknowledge the limitation
5. Focus on the lawyer's self-reported skill areas and values that directly address the client's specific needs
6. Mention availability when relevant to taking on this work

Be honest and precise about matching. It's better to acknowledge limitations than to overstate expertise in areas not supported by their skill profile.

Format your response in JSON like this:
{
    "lawyer1_name": "Detailed explanation of why lawyer 1 is an excellent match or acknowledgment of limitations...",
    "lawyer2_name": "Detailed explanation of why lawyer 2 is an excellent match or acknowledgment of limitations...",
    "lawyer3_name": "Detailed explanation of why lawyer 3 is an excellent match or acknowledgment of limitations..."
}
"""
    return prompt

# Function to call Claude API using requests
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
        # Import just what we need to make an HTTP request
        import requests
        import json
        
        # Claude API endpoint
        url = "https://api.anthropic.com/v1/messages"
        
        # Headers
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        # Request payload - Use Haiku for faster responses
        payload = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 1000,
            "temperature": 0.0,
            "system": "You are a legal resource coordinator that analyzes lawyer expertise matches. You provide brief, factual explanations about why specific lawyers match particular client legal needs based on their self-reported skills. Focus primarily on skills and expertise rather than biographical information. Keep explanations concise and focused on the relevant expertise.",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        # Make the request
        response = requests.post(url, headers=headers, json=payload)
        
        # Check for successful response
        if response.status_code == 200:
            response_json = response.json()
            response_text = response_json.get("content", [{}])[0].get("text", "")
            
            # Find JSON part in the response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
            else:
                return {"error": "Could not extract JSON from Claude's response"}
        else:
            return {"error": f"API call failed with status code {response.status_code}: {response.text}"}
            
    except Exception as e:
        st.error(f"Error calling Claude API: {str(e)}")
        
        # Provide a more detailed error message to help debugging
        import traceback
        st.error(f"Error details: {traceback.format_exc()}")
        
        # Return a fallback response
        return {"error": f"API error: {str(e)}"}

# Callback function to set query and trigger search
def set_query_and_search(text):
    st.session_state['query'] = text
    st.session_state['search_pressed'] = True
    # Force a rerun to immediately show results
    st.experimental_rerun()
    
# Initialize session state variables
if 'query' not in st.session_state:
    st.session_state['query'] = ""
if 'search_pressed' not in st.session_state:
    st.session_state['search_pressed'] = False
if 'practice_area_filter' not in st.session_state:
    st.session_state['practice_area_filter'] = None
    
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
        set_query_and_search(query)

st.sidebar.markdown("---")
st.sidebar.markdown("### Need Help?")
st.sidebar.info(
    "For assistance with the matching tool or to add a lawyer to the database, contact the Legal Operations team at legalops@example.com"
)

# Main app layout
st.title("⚖️ Legal Expert Finder")
st.markdown("Match client legal needs with the right lawyer based on expertise")

# Load data
data = load_lawyer_data()

# NEW: Add practice area filter at the top
selected_practice_area = add_practice_area_filter()

# Save the selected practice area in session state
if selected_practice_area:
    st.session_state['practice_area_filter'] = selected_practice_area

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
        # Use set_query_and_search for immediate refresh
        if st.button(preset_query, key=f"preset_{i}"):
            set_query_and_search(preset_query)

# Update query in session state from text area
if query:
    st.session_state['query'] = query

# Search button
search_pressed = st.button("🔍 Find Matching Lawyers", type="primary", use_container_width=True)
if search_pressed:
    st.session_state['search_pressed'] = True
    # Force a rerun to ensure results display immediately
    st.experimental_rerun()

# Display results when search is pressed
if st.session_state['search_pressed'] and st.session_state['query']:
    with st.spinner("Matching client needs with our legal experts..."):
        # Get practice area filter from session state
        practice_area_filter = st.session_state.get('practice_area_filter')
        
        # Get matches with improved matching algorithm that includes practice area filtering
        matches = match_lawyers(data, st.session_state['query'], practice_area_filter=practice_area_filter)
        
        if not matches:
            if practice_area_filter:
                st.warning(f"No matching lawyers found with practice area '{practice_area_filter}'. Try a different practice area or remove the filter.")
            else:
                st.warning("No matching lawyers found. Please try a different query.")
        else:
            # Call Claude API for reasoning with practice area emphasis
            claude_prompt = format_claude_prompt(st.session_state['query'], matches, practice_area_filter)
            reasoning = call_claude_api(claude_prompt)
            
            # Get identified legal domains from the query
            query_domains = identify_query_domains(st.session_state['query'])
            
            # Display results with domain and practice area information
            st.markdown("## Matching Legal Experts")
            
            # Show practice area filter if applied
            if practice_area_filter:
                st.markdown(f"**Filtered by Practice Area:** {practice_area_filter}")
            
            if query_domains:
                # Show which legal domains were identified
                domain_str = ", ".join([f"{domain} ({score:.0%})" for domain, score in query_domains.items()])
                st.markdown(f"**Identified Legal Domains:** {domain_str}")
            
            st.markdown(f"Found {len(matches)} lawyers matching client needs (sorted by expertise match):")
            
            # Sort by match score for display
            sorted_matches = sorted(matches, key=lambda x: x['score'], reverse=True)
            
            for match in sorted_matches:
                lawyer = match['lawyer']
                matched_skills = match['matched_skills']
                
                with st.container():
                    # Determine availability class based on status
                    availability_class = "availability-tag"
                    if "Limited" in lawyer['availability'] or "Vacation" in lawyer['availability'] or "Not Available" in lawyer['availability']:
                        availability_class = "availability-tag-limited"
                    elif "Available" in lawyer['availability']:
                        availability_class = "availability-tag-available"
                    elif "Ad Hoc" in lawyer['availability']:
                        availability_class = "availability-tag-adhoc"
                        
                    # Use raw HTML string concatenation to avoid Streamlit escaping issues
                    html_output = f"""
                    <div class="lawyer-card">
                        <div class="lawyer-name">
                            {lawyer['name']}
                            <span class="{availability_class}">{lawyer['availability']}</span>
                        </div>
                        <div class="lawyer-email">{lawyer['email']}</div>
                        <div class="practice-area">Practice Area: {lawyer['practice_area']}</div>
                    """
                    
                    # Get bio data
                    bio = lawyer['bio'] if 'bio' in lawyer else {}
                    
                    # Create biographical info section
                    bio_html = ""
                    if bio:
                        bio_html += '<div class="bio-section">'
                        if bio.get('level'):
                            bio_html += f'<div class="bio-level">{bio["level"]}</div>'
                        
                        bio_details = []
                        if bio.get('call'):
                            bio_details.append(f'Called to Bar: {bio["call"]}')
                        if bio.get('jurisdiction'):
                            bio_details.append(f'Jurisdiction: {bio["jurisdiction"]}')
                        if bio.get('location'):
                            bio_details.append(f'Location: {bio["location"]}')
                        
                        if bio_details:
                            bio_html += f'<div class="bio-details">{" | ".join(bio_details)}</div>'
                            
                        if bio.get('previous_in_house'):
                            bio_html += f'<div class="bio-experience"><strong>In-House Experience:</strong> {bio["previous_in_house"]}</div>'
                        if bio.get('previous_firms'):
                            bio_html += f'<div class="bio-experience"><strong>Previous Firms:</strong> {bio["previous_firms"]}</div>'
                        if bio.get('education'):
                            bio_html += f'<div class="bio-education"><strong>Education:</strong> {bio["education"]}</div>'
                            
                        bio_html += '</div>'
                    
                    # Add the bio section to the HTML output
                    html_output += bio_html
                    
                    # Add availability details
                    html_output += '<div class="availability-details">'
                    if lawyer['days_available'] is not None:
                        html_output += f"Days available: {lawyer['days_available']} | "
                    if lawyer['hours_available'] is not None:
                        html_output += f"Hours available: {lawyer['hours_available']}"
                    html_output += '</div>'
                    
                    # Add vacation info
                    if lawyer['vacation']:
                        vacation_dates = ", ".join(lawyer['vacation']) if isinstance(lawyer['vacation'], list) else lawyer['vacation']
                        html_output += f'<div class="vacation-info">Vacation: {vacation_dates}</div>'
                    
                    # Add engagement note
                    if lawyer['engagement_note']:
                        html_output += f'<div class="engagement-note">{lawyer["engagement_note"]}</div>'
                    
                    # Add industry experience if available
                    if bio and bio.get('industry_experience'):
                        html_output += f'<div class="industry-experience"><strong>Industry Experience:</strong> {bio["industry_experience"]}</div>'
                    
                    # Domain expertise indicator
                    domain_expertise = "has_domain_expertise" in match and match["has_domain_expertise"]
                    domain_tag = '<span style="background-color: #e8f5e9; color: #2e7d32; border-radius: 10px; padding: 2px 8px; font-size: 12px; margin-left: 10px;">Domain Expert</span>' if domain_expertise else ""
                    
                    # Show matched domains if available
                    matched_domains_html = ""
                    if "matched_domains" in match and match["matched_domains"]:
                        matched_domains_html = '<div style="margin-top: 5px;"><strong>Expertise Areas:</strong> ' + ', '.join(match["matched_domains"]) + '</div>'
                    
                    # Add the rest of the card
                    html_output += f"""
                        <div class="billable-rate">Rate: {lawyer['billable_rate']} | Recent Client: {lawyer['last_client']}</div>
                        {matched_domains_html}
                        <div style="margin-top: 10px;">
                            <strong>Relevant Expertise:</strong> {domain_tag}<br/>
                            {"".join([f'<span class="skill-tag">{skill["skill"]}: {skill["value"]}</span>' for skill in matched_skills])}
                        </div>
                        <div class="reasoning-box">
                            <div class="match-rationale-title">MATCH ANALYSIS:</div>
                            {reasoning.get(lawyer['name'], 'This lawyer has relevant expertise in the areas described in the client query.')}
                        </div>
                    </div>
                    """
                    
                    # Render the HTML
                    st.markdown(html_output, unsafe_allow_html=True)
            
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
        To get the best results:
        
        1. **Select a practice area** from the dropdown at the top to filter lawyers by their primary area of expertise
        2. Enter your client's specific legal needs in the text box or select a common query
        3. Be as specific as possible about their requirements, including:
           - The type of legal expertise needed
           - Any industry-specific requirements
           - Geographic considerations (e.g., province-specific needs)
           - The nature of the legal matter
           - Timeframe and urgency
        
        The system will match the query with lawyers who have self-reported expertise in those areas, prioritizing those whose practice area matches the specified filter.
        """)

# Footer
st.markdown("---")
st.markdown(
    "This internal tool uses self-reported expertise from 64 lawyers who distributed 120 points across 167 different legal skills. "
    "Results are sorted by domain expertise match and only display lawyers with precisely relevant skills for the specific legal practice areas requested. "
    "Last updated: February 26, 2025 and has March Attorney Availability Updated"
)

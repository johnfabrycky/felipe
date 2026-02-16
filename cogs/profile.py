import discord
from discord.ext import commands
from discord import app_commands
import json
import os

# --- DATA CONFIGURATION ---
DATA_FILE = "user_profiles.json"

# --- ROLE CONFIGURATION (REPLACE ZEROS WITH YOUR REAL DISCORD ROLE IDS) ---
YEAR_ROLE_IDS = {
    "Freshman": 000000000000000000,
    "Sophomore": 000000000000000000,
    "Junior": 000000000000000000,
    "Senior": 000000000000000000,
    "Grad Student": 000000000000000000
}

# Top 20 Most Popular UIUC Majors mapped to Role IDs
MAJOR_ROLE_IDS = {
    "Psychology": 000000000000000000,
    "Computer Science": 000000000000000000,
    "Computer Engineering": 000000000000000000,
    "Accountancy": 000000000000000000,
    "Finance": 000000000000000000,
    "Economics": 000000000000000000,
    "Communication": 000000000000000000,
    "Architecture": 000000000000000000,
    "Anthropology": 000000000000000000,
    "Mechanical Engineering": 000000000000000000,
    "Engineering Mechanics": 000000000000000000,
    "Biomedical Engineering": 000000000000000000,
    "Chemical Engineering": 000000000000000000,
    "Industrial Engineering": 000000000000000000,
    "Material Sciences": 000000000000000000,
    "Political Science": 000000000000000000,
    "Agricultural & Consumer Economics": 000000000000000000,
    "ETMAS": 000000000000000000,
    "Molecular & Cellular Biology": 000000000000000000,
    "Electrical Engineering": 000000000000000000,
    "Civil Engineering": 000000000000000000,
    "Advertising": 000000000000000000,
    "Animal Sciences": 000000000000000000,
    "Kinesiology": 000000000000000000,
    "Aerospace Engineering": 000000000000000000,
    "Mathematics": 000000000000000000,
    "Statistics": 000000000000000000,
    "Community Health": 000000000000000000,
    "Data Science": 000000000000000000,
    "Information Sciences": 000000000000000000
}

# This list is used ONLY for autocomplete suggestions.
MAJORS = [
    "ACES Undeclared", "Accountancy, BS", "Accountancy + Data Science, BS", "Actuarial Science, BSLAS",
    "Advertising, BS", "Aerospace Engineering, BS", "African American Studies, BALAS",
    "Agricultural & Biological Engineering, BS", "Bioprocess Engineering and Industrial Biotechnology",
    "Off-Highway Vehicle and Equipment Engineering", "Renewable Energy Systems Engineering",
    "Soil and Water Resources Engineering", "Sustainable Ecological and Environmental Systems Engineering",
    "Synthetic Biological Engineering", "Ag & Bio Engineering (Dual Degree)", 
    "Agricultural & Consumer Economics, BS", "Agri-Accounting", "Agribusiness Markets & Management",
    "Consumer Economics & Finance", "Environmental Economics & Policy", "Farm Management",
    "Finance in Agribusiness", "Financial Planning", "Policy, International Trade & Development",
    "Public Policy & Law", "Agricultural Leadership, Education, & Communications, BS",
    "Agricultural Communications", "Agricultural Education", "Organizational & Community Leadership",
    "Agronomy, BS", "Animal Sciences, BS", "Companion Animal & Equine Science",
    "Food Animal Production & Management", "Science, Pre-Veterinary & Medical", "Anthropology, BALAS",
    "Archaeology", "Biological Anthropology", "Human Evolutionary Biology",
    "Sociocultural & Linguistic Anthropology", "Architectural Studies, BS", "Art & Art History, BFA",
    "Art Education, BFA", "Art History, BALAS", "Art Undeclared", "Asian American Studies, BALAS",
    "Astronomy, BSLAS", "Astronomy + Data Science, BSLAS", "Astrophysics, BSLAS",
    "Atmospheric Sciences, BSLAS", "Biochemistry, BS", "Bioengineering, BS",
    "Brain & Cognitive Science, BSLAS", "Business + Data Science, BS", "Business Undeclared",
    "Chemical Engineering, BS", "Biomolecular Engineering", "Chemical Engineering + Data Science, BS",
    "Chemistry, BS", "Environmental Chemistry", "Chemistry, BSLAS", "Civil Engineering, BS",
    "Classics, BALAS", "Classical Civilizations", "Classical Languages", "Communication, BALAS",
    "Community Health, BS", "Health Education", "Health Planning & Administration",
    "Rehabilitation & Disability Studies", "Community Health, BS & Public Health, MPH",
    "Comparative & World Literature, BALAS", "Comparative Literature", "World Literature",
    "Computer Engineering, BS", "Computer Science + Advertising, BS", "Computer Science + Animal Sciences, BS",
    "Computer Science + Anthropology, BSLAS", "Computer Science + Astronomy, BSLAS",
    "Computer Science + Bioengineering, BS", "Computer Science + Chemistry, BSLAS",
    "Computer Science + Crop Sciences, BS", "Computer Science + Economics, BSLAS",
    "Computer Science + Education, BS", "Learning Sciences", "Secondary Education",
    "Computer Science + Geography & GIS, BSLAS", "Computer Science + Linguistics, BSLAS",
    "Computer Science + Music, BS", "Computer Science + Physics, BS", "Computer Science + Philosophy, BSLAS",
    "Computer Science, BS", "Creative Writing, BALAS", "Crop Sciences, BS", "Agroecology",
    "Crop Agribusiness", "Horticultural Food Systems", "Dance, BA", "Dance, BA & Kinesiology, BS",
    "Dance, BFA", "Dietetics and Nutrition, BS", "Early Childhood Education, BS",
    "Professional Education - Licensure", "Professional Education - Non-Licensure",
    "Earth, Society, & Environmental Sustainability, BSLAS", "Science of the Earth System (SES)",
    "Society and the Environment", "East Asian Languages & Cultures, BALAS",
    "Econometrics & Quantitative Economics, BSLAS", "Economics, BALAS", "Electrical Engineering, BS",
    "Elementary Education, BS", "Engineering Mechanics, BS",
    "Engineering Tech & Management for Ag Systems, BS", "Agricultural Production & Processing",
    "Construction Management", "Digital & Precision Agriculture", "Energy & the Environment",
    "Engineering Undeclared", "English, BALAS", "English Teaching", "Topics in English",
    "Environmental Engineering, BS", "Finance, BS", "Finance + Data Science, BS", "Food Science, BS",
    "French (Teaching), BA", "French, BALAS", "French Studies", "Gender & Women's Studies, BALAS",
    "Geography & Geographic Information Science, BALAS", "General Geography", "Human Geography",
    "Geography & Geographic Information Science, BSLAS", "Geographic Information Science",
    "Physical Geography", "Geology, BS", "Environmental Geology", "Geophysics", "Geology, BSLAS",
    "Earth & Environmental Sciences", "Earth Science Teaching", "Germanic Studies, BALAS",
    "German Business & Commercial Studies", "German Studies", "Scandinavian Studies",
    "German (Teaching), BA", "Global Studies, BALAS", "Graphic Design, BFA", "History of Art, BALAS",
    "History, BALAS", "History Teaching", "Hospitality Management, BS",
    "Human Development & Family Studies, BS", "Individual Plans of Study, BALAS or BSLAS",
    "Industrial Design, BFA", "Industrial Engineering, BS", "Information Sciences, BS",
    "Information Sciences + Data Science, BS", "Information Systems, BS",
    "Innovation, Leadership & Eng. Entrepreneurship, BS", "Instrumental Music, BMUS",
    "Integrative Biology, BSLAS", "Integrative Biology Honors", "Interdisciplinary Health Sciences, BS",
    "Health & Aging", "Health Behavior Change", "Health Diversity", "Health Technology",
    "Interdisciplinary Studies, BALAS", "Jewish Studies", "Medieval Studies", "Italian, BALAS",
    "Jazz Performance, BMUS", "Journalism, BS", "Kinesiology, BS", "Teacher Education (K-12)",
    "Kinesiology, BS & Public Health, MPH", "Landscape Architecture, BLA", "Latin American Studies, BALAS",
    "Latina/Latino Studies, BALAS", "Learning & Education Studies, BS",
    "Educational Equality & Cultural Understanding", "Educational Technology",
    "Inclusive Leadership & Learning in Organizations", "Workplace Training & Development",
    "Liberal Studies, BLS", "Global Perspectives", "Health and Society", "Management Studies",
    "Linguistics, BALAS", "Linguistics & TESL, BALAS", "Lyric Theatre, BMA", "Creative", "Performance",
    "Management, BS", "Marketing, BS", "Materials Science & Engineering, BS",
    "Materials Science & Engineering + Data Science, BS", "Mathematics & Computer Science, BSLAS",
    "Mathematics, BSLAS", "Applied Mathematics", "Data Optimization", "Math Doctoral Preparation",
    "Teaching of Mathematics", "Mechanical Engineering, BS", "Media, BA", "Media & Cinema Studies, BS",
    "Middle Grades Education, BS", "Literacy", "Mathematics", "Science", "Social Science",
    "Molecular & Cellular Biology, BSLAS", "Honors Concentration", "MCB + Data Science, BSLAS",
    "Music, BA", "Music Technology", "Music Composition, BMUS", "Music - Computer Science & Music, BS",
    "Music Education, BME", "Choral Music", "General Music", "Instrumental Music", "Technology",
    "Music - Instrumental Music, BMUS", "Music - Jazz Performance, BMUS", "Music - Open Studies, BMUS",
    "Music - Voice, BMUS", "Musicology, BMUS", "Natural Resources & Environmental Sciences, BS",
    "Ecosystem Stewardship & Restoration Ecology", "Environmental Science & Management",
    "Environmental Social Sciences", "Fish, Wildlife & Conservation Biology", "Neural Engineering, BS",
    "Neuroscience, BSLAS", "Nuclear, Plasma, & Radiological Engineering, BS",
    "Plasma & Fusion Science & Engineering", "Power, Safety & Environment",
    "Radiological, Medical & Instrumentation Applications", "NPRE + Data Science, BS",
    "Nutrition and Health, BS", "Operations Management, BS", "Philosophy, BALAS", "Physics, BS",
    "Plant Biotechnology, BS", "Political Science, BALAS", "Citizen Politics", "Civic Leadership",
    "General Political Science", "International Relations", "Law & Power",
    "Public Policy & Democratic Institution", "World Politics", "Portuguese, BALAS", "Psychology, BSLAS",
    "Behavioral Neuroscience", "Clinical/Community Psychology", "Cognitive Neuroscience",
    "Cognitive Psychology", "Developmental Psychology", "Diversity Science",
    "Intradisciplinary Psychology", "Organizational Psychology", "Personality Psychology",
    "Social Psychology", "Recreation, Sport & Tourism, BS", "Recreation Management", "Sports Management",
    "Tourism Management", "Religion, BALAS", "Russian, East European, & Eurasian Studies, BALAS",
    "Secondary Education, BS", "Slavic Studies, BALAS", "Czech Studies", "Polish Studies",
    "Russian Language, Literature, & Culture", "South Slavic Studies", "Ukranian Studies",
    "Social Work, BSW", "Sociology, BALAS", "Spanish (Teaching), BA", "Spanish, BALAS",
    "Special Education, BS", "Speech & Hearing Science, BS", "Audiology",
    "Cultural-Linguistic Diversity", "Neuroscience of Communication", "Speech Language Pathology",
    "Statistics & Computer Science, BSLAS", "Statistics, BSLAS",
    "Strategy, Innovation and Entrepreneurship, BS", "Studio Art, BASA", "Studio Art, BFASA", "Fashion",
    "Illustration", "Interdisciplinary Practice", "New Media", "Painting", "Photography", "Printmaking",
    "Sculpture", "Supply Chain Management, BS", "Sustainability in Food & Environmental Systems, BS",
    "Sustainable Design, BS", "Systems Engineering and Design, BS",
    "Teaching - Middle Grades Education, BS", "Teaching of French, BA", "Teaching of German, BA",
    "Teaching of Spanish, BA", "Theatre, BFA", "Acting", "Arts & Entertainment Technology",
    "Costume Design & Technology", "Lighting Design & Technology", "Scenic Design", "Scenic Technology",
    "Sound Design & Technology", "Stage Management", "Theatre Studies", "Urban Studies & Planning, BA",
    "Global Cities", "Policy & Planning", "Social Justice", "Sustainability", "Voice, BMUS"
]

class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.profiles = self.load_data()

    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_data(self):
        with open(DATA_FILE, 'w') as f:
            json.dump(self.profiles, f, indent=4)

    # --- AUTOCOMPLETE LOGIC ---
    async def major_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        user_input = current.lower()
        matches = [m for m in MAJORS if user_input in m.lower()]
        return [app_commands.Choice(name=m[:100], value=m[:100]) for m in matches[:25]]

    @app_commands.command(name="set_profile", description="Set your Major and Year in school")
    @app_commands.describe(major="Start typing your major...", year="Select your year")
    @app_commands.choices(year=[app_commands.Choice(name=y, value=y) for y in YEAR_ROLE_IDS.keys()])
    @app_commands.autocomplete(major=major_autocomplete)
    async def set_profile(self, interaction: discord.Interaction, major: str, year: str):
        # 1. Update the JSON Database
        user_id = str(interaction.user.id)
        self.profiles[user_id] = {
            "name": interaction.user.display_name,
            "major": major,
            "year": year
        }
        self.save_data()

        # 2. ROLE MANAGEMENT
        guild = interaction.guild
        member = interaction.user
        
        roles_to_add = []
        roles_to_remove = []
        feedback_messages = []

        # --- PROCESS YEAR ROLE ---
        target_year_id = YEAR_ROLE_IDS.get(year)
        if target_year_id:
            year_role = guild.get_role(target_year_id)
            if year_role:
                roles_to_add.append(year_role)
                # Remove other year roles
                for y_name, y_id in YEAR_ROLE_IDS.items():
                    if y_id != target_year_id:
                        old_role = guild.get_role(y_id)
                        if old_role and old_role in member.roles:
                            roles_to_remove.append(old_role)
            else:
                feedback_messages.append(f"⚠️ Config Error: Year role ID for '{year}' not found in server.")
        
        # --- PROCESS MAJOR ROLE ---
        # Only assign a role if the selected major is in our "Top 20" dictionary
        target_major_id = MAJOR_ROLE_IDS.get(major)
        
        if target_major_id:
            major_role = guild.get_role(target_major_id)
            if major_role:
                roles_to_add.append(major_role)
                # Remove any OTHER Top 20 major roles they might have
                for m_name, m_id in MAJOR_ROLE_IDS.items():
                    if m_id != target_major_id:
                        old_role = guild.get_role(m_id)
                        if old_role and old_role in member.roles:
                            roles_to_remove.append(old_role)
            else:
                feedback_messages.append(f"⚠️ Config Error: Major role ID for '{major}' not found in server.")
        else:
            # User selected a major that isn't in the Top 20 dict.
            # We verify if they hold any OLD Top 20 roles and remove them (switching from CS -> Jazz Performance)
            for m_name, m_id in MAJOR_ROLE_IDS.items():
                old_role = guild.get_role(m_id)
                if old_role and old_role in member.roles:
                    roles_to_remove.append(old_role)
            
            feedback_messages.append(f"ℹ️ Profile updated, but no specific role exists for **{major}**.")

        # --- APPLY CHANGES ---
        try:
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove)
            if roles_to_add:
                await member.add_roles(*roles_to_add)
        except discord.Forbidden:
            return await interaction.response.send_message("❌ I don't have permission to change roles! Check bot hierarchy.", ephemeral=True)

        # --- SEND RESPONSE ---
        embed = discord.Embed(title="✅ Profile Updated", color=discord.Color.green())
        embed.add_field(name="Major", value=major, inline=True)
        embed.add_field(name="Year", value=year, inline=True)
        
        if feedback_messages:
            embed.add_field(name="Notices", value="\n".join(feedback_messages), inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="profile", description="View a user's profile")
    async def view_profile(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        user_id = str(target.id)
        
        data = self.profiles.get(user_id)
        
        if not data:
            msg = f"{target.display_name} hasn't set up a profile yet."
            if target == interaction.user:
                msg += " Use `/set_profile` to set yours!"
            return await interaction.response.send_message(msg, ephemeral=True)

        embed = discord.Embed(title=f"🎓 {target.display_name}'s Profile", color=discord.Color.blue())
        embed.add_field(name="Major", value=data.get('major', 'Unknown'), inline=False)
        embed.add_field(name="Year", value=data.get('year', 'Unknown'), inline=False)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Profile(bot))
"""
Static knowledge base for the AI Resume Analyzer.
Contains skill taxonomies, job-role skill profiles, course catalog,
interview question banks, and action-verb lists.

Kept as plain Python data (instead of external ML model downloads)
so the app runs fully offline.
"""

PROGRAMMING_LANGUAGES = [
    "python", "java", "javascript", "typescript", "c++", "c", "c#", "go",
    "golang", "rust", "kotlin", "swift", "php", "ruby", "scala", "r",
    "matlab", "dart", "perl", "sql",
]

FRAMEWORKS = [
    "react", "angular", "vue", "next.js", "nextjs", "node.js", "nodejs",
    "express", "django", "flask", "fastapi", "spring", "spring boot",
    ".net", "asp.net", "laravel", "rails", "ruby on rails", "bootstrap",
    "tailwind", "jquery", "redux", "graphql",
]

DATABASES = [
    "mysql", "postgresql", "postgres", "mongodb", "sqlite", "oracle",
    "redis", "cassandra", "dynamodb", "firebase", "mariadb", "elasticsearch",
    "neo4j", "couchdb",
]

CLOUD_TECH = [
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes",
    "terraform", "jenkins", "ci/cd", "cloudformation", "lambda",
    "ec2", "s3", "heroku", "vercel", "netlify", "openshift",
]

DEV_TOOLS = [
    "git", "github", "gitlab", "bitbucket", "jira", "confluence",
    "postman", "vs code", "intellij", "eclipse", "figma", "linux",
    "bash", "webpack", "npm", "yarn", "maven", "gradle",
]

DATA_ML = [
    "machine learning", "deep learning", "tensorflow", "pytorch",
    "scikit-learn", "pandas", "numpy", "keras", "nlp", "computer vision",
    "data analysis", "data visualization", "tableau", "power bi",
    "spark", "hadoop", "opencv", "matplotlib", "seaborn",
]

SOFT_SKILLS = [
    "communication", "leadership", "teamwork", "problem solving",
    "critical thinking", "time management", "adaptability", "creativity",
    "collaboration", "presentation", "negotiation", "mentoring",
    "project management", "decision making", "conflict resolution",
]

ALL_TECHNICAL_SKILLS = sorted(set(
    PROGRAMMING_LANGUAGES + FRAMEWORKS + DATABASES + CLOUD_TECH + DEV_TOOLS + DATA_ML
))

# Job role -> set of representative required skills (used for prediction & gap analysis)
JOB_ROLE_SKILLS = {
    "Software Engineer": ["python", "java", "git", "sql", "data structures", "algorithms", "linux"],
    "Frontend Developer": ["javascript", "react", "html", "css", "typescript", "bootstrap", "tailwind", "redux"],
    "Backend Developer": ["python", "java", "node.js", "django", "flask", "spring boot", "sql", "mongodb", "rest api"],
    "Full Stack Developer": ["javascript", "react", "node.js", "express", "mongodb", "sql", "python", "git"],
    "Java Developer": ["java", "spring", "spring boot", "hibernate", "sql", "maven", "git"],
    "Python Developer": ["python", "django", "flask", "fastapi", "sql", "pandas", "numpy", "git"],
    "Cloud Engineer": ["aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ci/cd", "linux"],
    "Data Analyst": ["sql", "python", "excel", "tableau", "power bi", "pandas", "data visualization", "statistics"],
    "Machine Learning Engineer": ["python", "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy", "machine learning", "deep learning"],
    "Cyber Security Analyst": ["network security", "linux", "python", "siem", "penetration testing", "firewalls", "encryption"],
}

# Course catalog used for recommendations
COURSE_CATALOG = [
    {"name": "AWS Cloud Practitioner", "difficulty": "Beginner", "duration": "4 weeks", "skills": ["aws", "cloud"]},
    {"name": "Python for Everybody", "difficulty": "Beginner", "duration": "6 weeks", "skills": ["python"]},
    {"name": "Java Programming Masterclass", "difficulty": "Intermediate", "duration": "8 weeks", "skills": ["java"]},
    {"name": "Data Structures & Algorithms", "difficulty": "Intermediate", "duration": "10 weeks", "skills": ["data structures", "algorithms"]},
    {"name": "React - The Complete Guide", "difficulty": "Intermediate", "duration": "6 weeks", "skills": ["react", "javascript"]},
    {"name": "Node.js Developer Course", "difficulty": "Intermediate", "duration": "5 weeks", "skills": ["node.js", "express"]},
    {"name": "Docker & Kubernetes", "difficulty": "Advanced", "duration": "4 weeks", "skills": ["docker", "kubernetes"]},
    {"name": "The Complete SQL Bootcamp", "difficulty": "Beginner", "duration": "3 weeks", "skills": ["sql"]},
    {"name": "MongoDB - The Complete Guide", "difficulty": "Intermediate", "duration": "3 weeks", "skills": ["mongodb"]},
    {"name": "Machine Learning A-Z", "difficulty": "Advanced", "duration": "12 weeks", "skills": ["machine learning", "python"]},
]

INTERVIEW_QUESTIONS = {
    "technical": [
        "Explain the difference between a list and a tuple in Python.",
        "What is the time complexity of binary search and why?",
        "How does garbage collection work in Java?",
        "Explain RESTful API design principles.",
        "What is the difference between SQL and NoSQL databases?",
        "Describe how indexing improves database query performance.",
        "What is the difference between process and thread?",
        "Explain the concept of normalization in databases.",
    ],
    "coding": [
        "Reverse a linked list in O(n) time.",
        "Find the longest substring without repeating characters.",
        "Implement a function to check if a binary tree is balanced.",
        "Given an array, find two numbers that add up to a target sum.",
        "Implement a LRU cache.",
    ],
    "hr": [
        "Tell me about yourself.",
        "Why do you want to work for this company?",
        "What are your strengths and weaknesses?",
        "Where do you see yourself in 5 years?",
        "Why should we hire you?",
    ],
    "behavioral": [
        "Describe a time you faced a conflict with a teammate and how you resolved it.",
        "Tell me about a project you're most proud of and why.",
        "Describe a situation where you had to learn something new quickly.",
        "Tell me about a time you failed and what you learned from it.",
        "How do you handle tight deadlines and pressure?",
    ],
    "tips": [
        "Research the company's products, mission, and recent news before the interview.",
        "Practice explaining your projects clearly using the STAR method.",
        "Prepare 2-3 thoughtful questions to ask the interviewer.",
        "Review fundamental data structures, algorithms, and your resume's technical claims.",
        "Do mock interviews to get comfortable speaking about your work out loud.",
    ],
}

STRONG_ACTION_VERBS = [
    "achieved", "architected", "automated", "built", "deployed", "designed",
    "developed", "engineered", "implemented", "improved", "increased",
    "launched", "led", "managed", "optimized", "reduced", "spearheaded",
    "streamlined", "transformed", "delivered", "established", "scaled",
]

WEAK_VERBS_TO_AVOID = [
    "responsible for", "worked on", "helped with", "involved in",
    "participated in", "assisted with", "duties included",
]

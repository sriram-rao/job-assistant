from __future__ import annotations

from typing import Iterable, Any


# Consolidated personal information
PERSON: dict[str, str | dict[str, str]] = {
    # Core Identity
    "first_name": "Sriram",
    "last_name": "Rao",
    "full_name": "Sriram Rao",
    "title": "Software Engineer",
    "location": "San Jose, CA",
    
    # Contact Information
    "contact": {
        "email": "reach@sriramrao.com",
        "phone": "+1 (949) 560-3250",
        "website": "sriramrao.com",
        "linkedin": "sriram-rao",
        "github": "sriram-rao"
    },
    
    # Professional Summary
    "tagline": (
        "Software engineer with industry and research experience in distributed data systems. "
        "Proven track record in developing efficient, resilient solutions and collaborating across teams "
        "to drive software innovation."
    )
}

SKILLS: dict[str, list[str]] = {
    "languages": [
        "Python", "C#", "Java", "C++", "C", "Ruby", "Swift", "Lisp", "Prolog", "SQL",
    ],
    "ui_ux": ["HTML", "CSS", "TypeScript", "JavaScript", "SwiftUI"],
    "automation": ["Bash", "Powershell", "Lua"],
    "databases": ["Big Data", "NoSQL", "MongoDB", "OLAP", "PostgreSQL", "Column-stores"],
    "compute_platforms": ["Spark", "ETL", "DAG", "Query Engine", "Apache Calcite", "Iceberg", "Trino"],
    "backend": [".NET", "Spring", "Flask", "REST", "SvelteKit", "Microservices", "AOP", "Architecture", "Caching"],
    "infrastructure": ["Docker", "AWS", "Azure", "CI/CD", "Custom IaC"],
}

EXPERIENCE: list[dict[str, str | list[str]]] = [
    {
        "company": "University of California, Irvine",
        "role": "Graduate Student Researcher",
        "start": "Sep 2020",
        "end": "Sep 2024",
        "location": "Irvine, CA",
        "bullets": [
            "Designed DB plugin balancing latency and costs for query-processing and ML-forecast loads.",
            "Developed framework for implicit simulator invocation (e.g., HYSPLIT) inside PostgreSQL.",
            "Created pipeline execution system for DAG-defined workflows (sample on GitHub: sriram-rao/rush).",
        ],
        "category": "academia",
    },
    {
        "company": "Dremio",
        "role": "Software Engineer - PhD Intern",
        "start": "Jun 2022",
        "end": "Sep 2022",
        "location": "Remote, CA",
        "bullets": [
            "POC for progressive query response in data lakes; worked with Apache Calcite and Iceberg.",
            "Improved row-count estimation in query planning via execution-observed statistics (LEO, Markl VLDB 2001).",
        ],
        "category": "industry",
    },
    {
        "company": "Microsoft",
        "role": "Software Engineer 2",
        "start": "Jun 2016",
        "end": "Sep 2020",
        "location": "Bengaluru, India",
        "bullets": [
            "Rebuilt ETL workflow manager for 100+ pipelines; deploy time from 1h to <5s.",
            "Piloted Spark Streaming POC for A/B significance 3x faster than batched method.",
            "Refactored Azure-hosted API caching via AOP; reduced config code 5x (~300 lines).",
            "Contributed to 40+ design reviews and 100+ code reviews; on-call issue support.",
        ],
        "category": "industry",
    },
    {
        "company": "Microsoft",
        "role": "Summer Intern",
        "start": "May 2015",
        "end": "Jun 2015",
        "location": "Bengaluru, India",
        "bullets": [
            "Analyzed insert/response times for Kusto, MongoDB, and a column-store under stress loads.",
            "Matched data stores to use-cases (log analysis vs aggregate queries).",
            "Enabled migration from OLAP cubes to column-store; ETL time from 10 days to 1 hour.",
        ],
        "category": "industry",
    },
    {
        "company": "Drexel University",
        "role": "Volunteer Intern",
        "start": "May 2025",
        "end": "Current",
        "location": "Remote, CA",
        "bullets": [
            "Building an iOS app to intuitively record and export a DBT mood journal.",
        ],
        "category": "industry",
    },
    {
        "company": "University of California, Irvine",
        "role": "Teaching Assistant",
        "start": "Sep 2020",
        "end": "Dec 2024",
        "location": "Irvine, CA",
        "bullets": [
            "Rated 4/5 by students; appreciated for database expertise and straightforward explanations.",
            "Coordinated slides, questions, assignments, and discussions for courses with 200+ students.",
        ],
        "category": "academia",
    },
]

EDUCATION: list[dict[str, object]] = [
    {
        "institution": "University of California, Irvine",
        "degree": "MS in Computer Science",
        "start": "Sep 2020",
        "end": "Mar 2025",
        "location": "Irvine, CA",
    },
    {
        "institution": "University of California, Irvine",
        "degree": "Graduate Work in the PhD Program",
        "start": "Sep 2020",
        "end": "Sep 2024",
        "location": "Irvine, CA",
        "notes": [
            "Advised by Prof. Sharad Mehrotra in data management: workload-aware pre-computation.",
        ],
    },
    {
        "institution": "National Institute of Technology, Karnataka",
        "degree": "B. Tech. in Computer Engineering",
        "start": "Jul 2012",
        "end": "Mar 2016",
        "location": "Surathkal, India",
    },
]

# Consolidated lists (skills/areas and packages)
SKILLS_CONSOLIDATED: dict[str, list[str]] = {
    # Core skill groups (superset of SKILLS)
    "languages": [
        "Python", "C#", "Java", "C++", "C", "Ruby", "Swift", "Lisp", "Prolog", "SQL",
    ],
    "frontend": [
        "HTML", "CSS", "JavaScript", "TypeScript",
        "Svelte", "SvelteKit", "TailwindCSS", "daisyui", 
    ],
    "automation": ["Bash", "Powershell", "Lua"],
    "databases": [
        "Big Data", "NoSQL", "MongoDB", "OLAP", "PostgreSQL", "Column-stores", "InfluxDB",
        "psycopg2", "pg", "mysql2",
    ],
    "compute_platforms": [
        "Spark", "ETL", "DAG", "Query Engine", "Apache Calcite", "Iceberg", "Trino",
        "Spark SQL",
    ],
    "backend": [
        ".NET", "Spring", "Flask", "REST", "Microservices", "AOP", "Architecture", "Caching",
        "Rails", 
    ],
    "infrastructure": ["Docker", "AWS", "Azure", "CI/CD", "Custom IaC"],
    "ios": ["SwiftUI"],
    # Conceptual areas
    "areas": [
        "Distributed data systems", "Databases & query engines", "ETL pipelines & DAGs",
        "Stream processing (Spark)", "Caching & microservices", "Cloud (Azure, AWS)", "CI/CD & IaC",
        "Workload-aware precomputation", "Simulator integration (HYSPLIT)", "A/B testing & experimentation",
        "API frameworks", "Incremental view maintenance", "Self-driving databases",
        "Serverless/actor systems (Orleans)", "Networks & middleware", "Cryptography (coursework)",
        "Progressive results", "Multiple-query optimization",
    ],
    # Ecosystems/topics from GitHub
    "ecosystems": ["neovim", "ios", "swift", "swiftui", "mobile-app",  "databases/sql"],
    # Organized popular packages into categories
    "data_science": [
        "NumPy", "Pandas", "Matplotlib", "SciPy", "Scikit-Learn", "GeoPandas",
        "Shapely", "Statsmodels", "XGBoost",
    ],
}

LETTER_CONTENT: dict[str, str] = {
    "Introduction": (
        "I am a software engineer with prior experience at Microsoft and the University of California, Irvine. "
        "I am interested in the {role} role at {company}. "
        "I am an excellent choice for this position."
    ),
    "Why do I want to join this company?": (
        "Having worked at Microsoft earlier, I reminisce about its inspiring atmosphere. "
        "I admire Microsoft AI’s mission to build systems that have true artificial intelligence. "
        "I understand how vital data systems are to build a high quality LLM and would love to participate in advancing Microsoft AI’s systems. "
        "With my technical background in robust, efficient systems, I would be a great addition to your team."
    ),
    "Why should this company pick me?": (
        "My skills and experience, in engineering and research, make me a great candidate. "
        "At Microsoft Ads, I rebuilt pipeline infrastructure used for the ETL of 100+ data workflows, cutting deployment time from 60 min to < 3 sec. "
        "I designed a Spark streaming POC to be 3x faster than the corresponding batched pipeline. "
        "I worked with cross-geography teams, building data-serving API frameworks to run on Azure. "
        "At UC Irvine, I designed a system to preprocess data deemed relevant by an AI-based workflow prediction model, "
        "trading off query latency with resource usage. I collaborated in cross-functional teams with IoT & civil engineers, chemists "
        "on APIs and metric dashboards to monitor drone data from a prescribed burn scenario."
    ),
    "Closing": (
        "Thank you for reading my letter. I look forward to the opportunity to discuss how my experience and skills can contribute to {company}."
    ),
}

# Defaults specific to cover letters
Letter: dict[str, str] = {
    # Letter basics
    "greeting": "Hello",
    "recipientfirstname": "Hiring Manager",
    "recipientlastname": "",
    "company": "Microsoft AI",
    "fullcompany": "Microsoft AI",
    "city": "Mountain View, ",
    "state": "CA",
    "country": "",
    # Roles and titles
    "mytitle": "Software Engineer",
    "jobtitle": "",
    "myindustryname": "large-scale systems",
    # Closers
    "closer": "Yours truly",
}


def flatten_person(person: dict[str, str | dict[str, str]]) -> dict[str, str]:
    """Flatten PERSON where values are str or dict[str, str] into str->str keys."""
    out: dict[str, str] = {}
    for k, v in person.items():
        if isinstance(v, str):
            out[k] = v
            continue
        [out.__setitem__(f"{k}_{sk}", sv) for sk, sv in v.items()]
    return out


def flatten_experience(experience: list[dict[str, Any]]) -> dict[str, str]:
    """Flatten EXPERIENCE into str->str using indexed prefixes."""
    flattened: dict[str, str] = {}
    for i, exp in enumerate(experience):
        prefix = f"exp_{i}"
        for key, value in exp.items():
            value: str | list[str] 
            if key != "bullets":
                flattened[f"{prefix}_{key}"] = str(value)
                continue

            [flattened.__setitem__(f"{prefix}_bullet_{j}", bullet) for j, bullet in enumerate(value)]
    return flattened


def get_details(
    overrides: dict[str, str] = {},
    include: Iterable[str] = ("common", "letter", "resume"),
) -> dict[str, str]:
    """
    Merge defaults from the selected sets and overlay user-provided overrides.
    include accepts any of: "common", "letter", "resume" (case-insensitive), 
    order matters for resolving collisions;
    Always returns a new dictionary object.
    """
    details: dict[str, dict[str, str]] = {
        "common": flatten_person(PERSON),
        "letter": Letter,
        "resume": flatten_experience(EXPERIENCE),
    }
    merged: dict[str, str] = {}
    merged = { key: value for name in include for key, value in details[name.lower()].items() }
    merged.update(overrides)
    return merged

"""Idempotently seed comprehensive, realistic academic data for ResearchBridge demos.

Seeds:
  - Skill vocabulary
  - Diverse users (Admin, Coordinator, Faculty, Students) with shared demo password
  - Student & Faculty profiles with skills and interests
  - Published and draft research opportunities with requirements
  - Applications in different workflow states (Submitted, Shortlisted, Accepted)
  - Active research projects and team memberships
  - Project milestones and assigned tasks
  - Shared project resources (papers, datasets, links)
  - AI Advisory recommendations & progress alerts
  - System notifications and activity audit entries
"""

from datetime import date, datetime, timedelta, timezone
import json

from sqlalchemy import select

from .db import Base, SessionLocal, engine
from .models import (
    ActivityLog,
    AgentRecommendation,
    Application,
    FacultyProfile,
    Milestone,
    Notification,
    Opportunity,
    OpportunitySkill,
    OpportunityVersion,
    Project,
    ProjectMember,
    Resource,
    Skill,
    StudentInterest,
    StudentProfile,
    StudentSkill,
    Task,
    User,
)
from .security import hash_password

DEMO_PASSWORD = "Password123!"

DEFAULT_SKILLS = {
    "Python": "Programming",
    "R": "Programming",
    "Java": "Programming",
    "C++": "Programming",
    "SQL": "Data",
    "Statistics": "Methods",
    "Machine Learning": "Data Science",
    "Artificial Intelligence": "Data Science",
    "Deep Learning": "Data Science",
    "Computer Vision": "Data Science",
    "Natural Language Processing": "Data Science",
    "Data Visualization": "Data",
    "Literature Review": "Research Methods",
    "Survey Design": "Research Methods",
    "Qualitative Analysis": "Research Methods",
    "Bioinformatics": "Domain Specific",
}


def seed_all() -> dict:
    Base.metadata.create_all(bind=engine)
    now = datetime.now(timezone.utc)
    today = date.today()
    counts = {}

    with SessionLocal() as session:
        # ── 1. Skills ──────────────────────────────────────────────────────────
        existing_skills = {name for (name,) in session.execute(select(Skill.name)).all()}
        skills_added = 0
        for name, category in DEFAULT_SKILLS.items():
            if name not in existing_skills:
                session.add(Skill(name=name, category=category))
                skills_added += 1
        session.commit()
        counts["skills_added"] = skills_added

        # ── 2. Users ───────────────────────────────────────────────────────────
        demo_users_data = [
            # Admins & Coordinators
            ("admin@researchbridge.edu", "Dr. Vikram Seth", "Administrator"),
            ("coordinator@ves.ac.in", "Prof. Ananya Iyer", "Coordinator"),
            # Faculty Mentors
            ("dr.sharma@ves.ac.in", "Dr. Rajesh Sharma", "Faculty"),
            ("prof.patel@ves.ac.in", "Prof. Sunita Patel", "Faculty"),
            # Student Researchers
            ("aarav.mehta@ves.ac.in", "Aarav Mehta", "Student"),
            ("priya.nair@ves.ac.in", "Priya Nair", "Student"),
            ("rohan.deshmukh@ves.ac.in", "Rohan Deshmukh", "Student"),
        ]

        users_by_email = {}
        for email, name, role in demo_users_data:
            user = session.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    email=email,
                    name=name,
                    role=role,
                    status="Active",
                    password_hash=hash_password(DEMO_PASSWORD),
                    verify_token=None,
                    created_at=now - timedelta(days=30),
                )
                session.add(user)
                session.flush()
            users_by_email[email] = user
        session.commit()
        counts["users_ready"] = len(users_by_email)

        # ── 3. Profiles ────────────────────────────────────────────────────────
        # Student: Aarav Mehta (AI & Medical Vision)
        aarav = users_by_email["aarav.mehta@ves.ac.in"]
        if not session.query(StudentProfile).filter(StudentProfile.user_id == aarav.id).first():
            p = StudentProfile(
                user_id=aarav.id,
                research_experience="Completed coursework in Deep Learning and Biomedical Image Processing. Built a PyTorch CNN for chest X-ray pneumonia classification.",
            )
            session.add(p)
            session.flush()
            for s in ["Python", "Machine Learning", "Deep Learning", "Computer Vision"]:
                session.add(StudentSkill(profile_id=p.id, skill_name=s))
            for i in ["Healthcare AI", "Medical Imaging", "Deep Learning"]:
                session.add(StudentInterest(profile_id=p.id, interest=i))

        # Student: Priya Nair (Epidemiology & Statistics)
        priya = users_by_email["priya.nair@ves.ac.in"]
        if not session.query(StudentProfile).filter(StudentProfile.user_id == priya.id).first():
            p = StudentProfile(
                user_id=priya.id,
                research_experience="Undergraduate research assistant in statistical modeling. Proficient with R, Python pandas, and cohort survey data analysis.",
            )
            session.add(p)
            session.flush()
            for s in ["Statistics", "R", "Python", "Data Visualization"]:
                session.add(StudentSkill(profile_id=p.id, skill_name=s))
            for i in ["Public Health", "Epidemiology", "Environmental Data"]:
                session.add(StudentInterest(profile_id=p.id, interest=i))

        # Student: Rohan Deshmukh (Human-Computer Interaction)
        rohan = users_by_email["rohan.deshmukh@ves.ac.in"]
        if not session.query(StudentProfile).filter(StudentProfile.user_id == rohan.id).first():
            p = StudentProfile(
                user_id=rohan.id,
                research_experience="Focused on user-centered research, accessibility evaluation, and mixed-method survey studies for educational platforms.",
            )
            session.add(p)
            session.flush()
            for s in ["Literature Review", "Survey Design", "Qualitative Analysis", "Python"]:
                session.add(StudentSkill(profile_id=p.id, skill_name=s))
            for i in ["Human-Computer Interaction", "Accessibility", "Educational Technology"]:
                session.add(StudentInterest(profile_id=p.id, interest=i))

        # Faculty: Dr. Rajesh Sharma (Biomedical AI)
        dr_sharma = users_by_email["dr.sharma@ves.ac.in"]
        if not session.query(FacultyProfile).filter(FacultyProfile.user_id == dr_sharma.id).first():
            session.add(
                FacultyProfile(
                    user_id=dr_sharma.id,
                    bio="Associate Professor in the Department of Computer Engineering. Principal Investigator at the Biomedical Computing & Machine Intelligence Lab.",
                    expertise=json.dumps(["Biomedical Imaging", "Deep Learning", "Clinical Decision Support"]),
                )
            )

        # Faculty: Prof. Sunita Patel (Environmental Data Science)
        prof_patel = users_by_email["prof.patel@ves.ac.in"]
        if not session.query(FacultyProfile).filter(FacultyProfile.user_id == prof_patel.id).first():
            session.add(
                FacultyProfile(
                    user_id=prof_patel.id,
                    bio="Assistant Professor specializing in environmental sensing, spatiotemporal air pollution forecasting, and applied machine learning.",
                    expertise=json.dumps(["Environmental Data Science", "Time Series Forecasting", "Spatial Statistics"]),
                )
            )
        session.commit()

        # ── 4. Opportunities ───────────────────────────────────────────────────
        opp1 = session.query(Opportunity).filter(Opportunity.title.like("%Diabetic Retinopathy%")).first()
        if not opp1:
            opp1 = Opportunity(
                faculty_id=dr_sharma.id,
                title="Deep Learning for Early Diabetic Retinopathy Screening",
                description="Investigating attention-based convolutional neural networks for automated microaneurysm detection in high-resolution fundus photography.",
                domain="Healthcare AI",
                duration="12 weeks",
                capacity=2,
                status="Published",
                deadline=today + timedelta(days=21),
                published_at=now - timedelta(days=14),
                requirements_version=1,
                created_at=now - timedelta(days=15),
            )
            session.add(opp1)
            session.flush()
            for s in ["Python", "Machine Learning", "Deep Learning", "Computer Vision"]:
                session.add(OpportunitySkill(opportunity_id=opp1.id, skill_name=s))
            session.add(
                OpportunityVersion(
                    opportunity_id=opp1.id,
                    version=1,
                    snapshot={
                        "title": opp1.title,
                        "description": opp1.description,
                        "domain": opp1.domain,
                        "capacity": opp1.capacity,
                        "required_skills": ["Python", "Machine Learning", "Deep Learning", "Computer Vision"],
                    },
                    created_at=now - timedelta(days=14),
                )
            )

        opp2 = session.query(Opportunity).filter(Opportunity.title.like("%Air Quality%")).first()
        if not opp2:
            opp2 = Opportunity(
                faculty_id=prof_patel.id,
                title="Urban Air Quality Index Analysis & Spatiotemporal Predictive Modeling",
                description="Developing predictive statistical and machine learning models for PM2.5 and PM10 particulate distribution across dense urban sensor networks.",
                domain="Environmental Data Science",
                duration="10 weeks",
                capacity=3,
                status="Published",
                deadline=today + timedelta(days=10),
                published_at=now - timedelta(days=7),
                requirements_version=1,
                created_at=now - timedelta(days=8),
            )
            session.add(opp2)
            session.flush()
            for s in ["Python", "Statistics", "Data Visualization", "Machine Learning"]:
                session.add(OpportunitySkill(opportunity_id=opp2.id, skill_name=s))
            session.add(
                OpportunityVersion(
                    opportunity_id=opp2.id,
                    version=1,
                    snapshot={
                        "title": opp2.title,
                        "description": opp2.description,
                        "domain": opp2.domain,
                        "capacity": opp2.capacity,
                        "required_skills": ["Python", "Statistics", "Data Visualization", "Machine Learning"],
                    },
                    created_at=now - timedelta(days=7),
                )
            )

        opp3 = session.query(Opportunity).filter(Opportunity.title.like("%Graph Neural Networks%")).first()
        if not opp3:
            opp3 = Opportunity(
                faculty_id=dr_sharma.id,
                title="Graph Neural Networks for Targeted Small-Molecule Drug Discovery",
                description="Exploratory investigation into molecular representation learning and binding affinity prediction on public bioassay datasets.",
                domain="Computational Biology",
                duration="16 weeks",
                capacity=1,
                status="Draft",
                deadline=today + timedelta(days=45),
                published_at=None,
                requirements_version=1,
                created_at=now - timedelta(days=3),
            )
            session.add(opp3)
            session.flush()
            for s in ["Python", "Machine Learning", "Bioinformatics"]:
                session.add(OpportunitySkill(opportunity_id=opp3.id, skill_name=s))
        session.commit()

        # ── 5. Applications ────────────────────────────────────────────────────
        # Application 1: Aarav -> Retinopathy Project (Accepted)
        app1 = session.query(Application).filter(Application.student_id == aarav.id, Application.opportunity_id == opp1.id).first()
        if not app1:
            app1 = Application(
                student_id=aarav.id,
                opportunity_id=opp1.id,
                motivation="I have hands-on experience training ResNet and Vision Transformer architectures on medical scans. I am eager to apply attention heatmaps to improve clinical interpretability for ophthalmologists.",
                profile_snapshot=json.dumps({"skills": ["Python", "Machine Learning", "Deep Learning", "Computer Vision"], "interests": ["Healthcare AI", "Medical Imaging"]}),
                req_version=1,
                status="Accepted",
                faculty_comment="Outstanding background in computer vision and strong alignment with our lab's current imaging grant.",
                submitted_at=now - timedelta(days=12),
                decided_at=now - timedelta(days=10),
            )
            session.add(app1)

        # Application 2: Priya -> Retinopathy Project (Shortlisted)
        app2 = session.query(Application).filter(Application.student_id == priya.id, Application.opportunity_id == opp1.id).first()
        if not app2:
            app2 = Application(
                student_id=priya.id,
                opportunity_id=opp1.id,
                motivation="While my core background is in statistical epidemiology, I want to lead the clinical data validation, cohort stratification, and bias analysis for the retinopathy model.",
                profile_snapshot=json.dumps({"skills": ["Statistics", "R", "Python", "Data Visualization"], "interests": ["Public Health", "Epidemiology"]}),
                req_version=1,
                status="Shortlisted",
                faculty_comment="Strong statistical background. Scheduled for follow-up lab interview regarding dataset validation tasks.",
                submitted_at=now - timedelta(days=6),
                decided_at=now - timedelta(days=2),
            )
            session.add(app2)

        # Application 3: Rohan -> Air Quality Project (Submitted)
        app3 = session.query(Application).filter(Application.student_id == rohan.id, Application.opportunity_id == opp2.id).first()
        if not app3:
            app3 = Application(
                student_id=rohan.id,
                opportunity_id=opp2.id,
                motivation="I am keen to explore how citizen-facing dashboards can communicate real-time air quality hazard data effectively to non-expert urban residents.",
                profile_snapshot=json.dumps({"skills": ["Literature Review", "Survey Design", "Python"], "interests": ["Human-Computer Interaction", "Accessibility"]}),
                req_version=1,
                status="Submitted",
                faculty_comment=None,
                submitted_at=now - timedelta(days=1),
                decided_at=None,
            )
            session.add(app3)

        # Application 4: Priya -> Air Quality Project (Accepted)
        app4 = session.query(Application).filter(Application.student_id == priya.id, Application.opportunity_id == opp2.id).first()
        if not app4:
            app4 = Application(
                student_id=priya.id,
                opportunity_id=opp2.id,
                motivation="My background in statistical modeling and spatial epidemiology is directly aligned with spatiotemporal PM2.5 forecasting.",
                profile_snapshot=json.dumps({"skills": ["Statistics", "R", "Python", "Data Visualization"], "interests": ["Public Health", "Environmental Health"]}),
                req_version=1,
                status="Accepted",
                faculty_comment="Excellent background in spatio-statistical modeling. Welcomed to the lab team.",
                submitted_at=now - timedelta(days=9),
                decided_at=now - timedelta(days=7),
            )
            session.add(app4)
        session.commit()

        # ── 6. Projects & Project Members (Workspace) ──────────────────────────
        proj1 = session.query(Project).filter(Project.title == "Retinopathy AI Lab Workspace").first()
        if not proj1:
            proj1 = Project(
                opportunity_id=opp1.id,
                title="Retinopathy AI Lab Workspace",
                description="Active collaborative research workspace for fundus image segmentation, augmentation pipelines, and model evaluation.",
                domain=opp1.domain,
                status="Active",
                created_at=now - timedelta(days=10),
            )
            session.add(proj1)
            session.flush()

            # Faculty Mentor as Lead
            session.add(ProjectMember(project_id=proj1.id, user_id=dr_sharma.id, role_in_project="Lead", joined_at=now - timedelta(days=10)))
            # Student Researcher as Member
            session.add(ProjectMember(project_id=proj1.id, user_id=aarav.id, role_in_project="Member", joined_at=now - timedelta(days=10)))

        # Project 2 for Prof. Sunita Patel (Urban Air Quality Lab)
        proj2 = session.query(Project).filter(Project.title == "Urban Air Quality Analytics Lab").first()
        if not proj2:
            proj2 = Project(
                opportunity_id=opp2.id,
                title="Urban Air Quality Analytics Lab",
                description="Collaborative research workspace investigating spatiotemporal GNNs for urban PM2.5 forecasting.",
                domain=opp2.domain,
                status="Active",
                created_at=now - timedelta(days=7),
            )
            session.add(proj2)
            session.flush()

            # Faculty Mentor as Lead
            session.add(ProjectMember(project_id=proj2.id, user_id=prof_patel.id, role_in_project="Lead", joined_at=now - timedelta(days=7)))
            # Student Researcher as Member
            session.add(ProjectMember(project_id=proj2.id, user_id=priya.id, role_in_project="Member", joined_at=now - timedelta(days=7)))

        # ── 7. Milestones & Tasks ──────────────────────────────────────────────
        m1 = session.query(Milestone).filter(Milestone.project_id == proj1.id, Milestone.description.like("%Literature%")).first()
        if not m1:
            m1 = Milestone(
                project_id=proj1.id,
                description="Literature review on Vision Transformers vs CNNs for fundus grading",
                target_date=today - timedelta(days=4),
                status="Completed",
                completed_at=now - timedelta(days=4),
                last_activity_at=now - timedelta(days=4),
            )
            session.add(m1)
            session.flush()

        m2 = session.query(Milestone).filter(Milestone.project_id == proj1.id, Milestone.description.like("%Preprocessing%")).first()
        if not m2:
            m2 = Milestone(
                project_id=proj1.id,
                description="Preprocessing, normalization, and CLAHE contrast enhancement on EyePACS fundus scans",
                target_date=today + timedelta(days=3),
                status="In Progress",
                completed_at=None,
                last_activity_at=now - timedelta(hours=6),
            )
            session.add(m2)
            session.flush()

            session.add(Task(milestone_id=m2.id, description="Implement CLAHE color enhancement script in OpenCV", status="Completed", assigned_to=aarav.id))
            session.add(Task(milestone_id=m2.id, description="Validate 512x512 downsampling without loss of small microaneurysm details", status="In Progress", assigned_to=aarav.id))

        m3 = session.query(Milestone).filter(Milestone.project_id == proj1.id, Milestone.description.like("%Benchmark%")).first()
        if not m3:
            m3 = Milestone(
                project_id=proj1.id,
                description="Train EfficientNet-B4 baseline and generate sensitivity-specificity curves",
                target_date=today + timedelta(days=20),
                status="Not Started",
                completed_at=None,
                last_activity_at=None,
            )
            session.add(m3)
            session.flush()
            session.add(Task(milestone_id=m3.id, description="Set up WandB experiment tracking and checkpointing", status="Not Started", assigned_to=aarav.id))

        # ── 8. Project Resources ───────────────────────────────────────────────
        r1 = session.query(Resource).filter(Resource.project_id == proj1.id, Resource.title.like("%Deep Residual Learning%")).first()
        if not r1:
            session.add(
                Resource(
                    project_id=proj1.id,
                    title="Deep Residual Learning for Image Recognition (ResNet)",
                    description="Seminal paper establishing residual skip-connections in deep convolutional networks.",
                    type="Paper",
                    storage_reference="https://arxiv.org/abs/1512.03385",
                    uploaded_by=dr_sharma.id,
                )
            )

        r2 = session.query(Resource).filter(Resource.project_id == proj1.id, Resource.title.like("%EyePACS%")).first()
        if not r2:
            session.add(
                Resource(
                    project_id=proj1.id,
                    title="EyePACS Diabetic Retinopathy Fundus Image Dataset",
                    description="Curated collection of 35,000+ labeled clinical fundus images with quality grades (0-4).",
                    type="Dataset",
                    storage_reference="https://www.kaggle.com/c/diabetic-retinopathy-detection",
                    uploaded_by=dr_sharma.id,
                )
            )

        # Milestones and Resources for proj2 (Urban Air Quality Analytics Lab)
        m2_1 = session.query(Milestone).filter(Milestone.project_id == proj2.id, Milestone.description.like("%Sensor%")).first()
        if not m2_1:
            m2_1 = Milestone(
                project_id=proj2.id,
                description="Sensor data pipeline integration and geospatial grid alignment",
                target_date=today - timedelta(days=2),
                status="Completed",
                completed_at=now - timedelta(days=2),
                last_activity_at=now - timedelta(days=2),
            )
            session.add(m2_1)
            session.flush()

        m2_2 = session.query(Milestone).filter(Milestone.project_id == proj2.id, Milestone.description.like("%Spatiotemporal%")).first()
        if not m2_2:
            m2_2 = Milestone(
                project_id=proj2.id,
                description="Spatiotemporal GNN model training on PM2.5 monitoring stations",
                target_date=today + timedelta(days=7),
                status="In Progress",
                completed_at=None,
                last_activity_at=now - timedelta(hours=3),
            )
            session.add(m2_2)
            session.flush()
            session.add(Task(milestone_id=m2_2.id, description="Tune temporal graph convolution window size", status="In Progress", assigned_to=priya.id))

        r2_1 = session.query(Resource).filter(Resource.project_id == proj2.id, Resource.title.like("%Spatiotemporal Graph%")).first()
        if not r2_1:
            session.add(
                Resource(
                    project_id=proj2.id,
                    title="Spatiotemporal Graph Neural Networks for Environmental Modeling",
                    description="Comprehensive survey on dynamic graph neural architectures applied to sensor time series.",
                    type="Paper",
                    storage_reference="https://arxiv.org/abs/2012.09600",
                    uploaded_by=prof_patel.id,
                )
            )

        # ── 9. AI Advisory Recommendations & Alerts (Member C / FR-025, FR-031)
        rec1 = session.query(AgentRecommendation).filter(AgentRecommendation.user_id == aarav.id, AgentRecommendation.reference_entity == f"opportunity:{opp1.id}").first()
        if not rec1:
            session.add(
                AgentRecommendation(
                    user_id=aarav.id,
                    type="opportunity",
                    reference_entity=f"opportunity:{opp1.id}",
                    reason_text="Matched 4 shared skills (Python, Machine Learning, Deep Learning, Computer Vision) and exact domain interest in Healthcare AI.",
                    score=48,
                    status="Active",
                    created_at=now - timedelta(days=14),
                )
            )

        rec2 = session.query(AgentRecommendation).filter(AgentRecommendation.user_id == priya.id, AgentRecommendation.reference_entity == f"opportunity:{opp2.id}").first()
        if not rec2:
            session.add(
                AgentRecommendation(
                    user_id=priya.id,
                    type="opportunity",
                    reference_entity=f"opportunity:{opp2.id}",
                    reason_text="Matched 3 required skills (Statistics, Python, Data Visualization) and environmental analytics interests.",
                    score=38,
                    status="Active",
                    created_at=now - timedelta(days=7),
                )
            )

        rec3 = session.query(AgentRecommendation).filter(AgentRecommendation.user_id == dr_sharma.id, AgentRecommendation.reference_entity == f"milestone:{m2.id}").first()
        if not rec3:
            session.add(
                AgentRecommendation(
                    user_id=dr_sharma.id,
                    type="alert",
                    reference_entity=f"milestone:{m2.id}",
                    reason_text="Milestone 'Preprocessing, normalization, and CLAHE' is due in 3 days. Recommend reviewing the OpenCV enhancement script.",
                    score=15,
                    status="Active",
                    created_at=now - timedelta(hours=12),
                )
            )

        # ── 10. Notifications & Audit Logs ─────────────────────────────────────
        n1 = session.query(Notification).filter(Notification.user_id == aarav.id, Notification.type == "Application Decision").first()
        if not n1:
            session.add(
                Notification(
                    user_id=aarav.id,
                    type="Application Decision",
                    message="Congratulations! Your research application for 'Deep Learning for Early Diabetic Retinopathy Screening' has been Accepted.",
                    related=f"application:{app1.id}",
                    read=False,
                    created_at=now - timedelta(days=10),
                )
            )

        n2 = session.query(Notification).filter(Notification.user_id == dr_sharma.id, Notification.type == "New Applicant").first()
        if not n2:
            session.add(
                Notification(
                    user_id=dr_sharma.id,
                    type="New Applicant",
                    message="Candidate Priya Nair has submitted an application for 'Deep Learning for Early Diabetic Retinopathy Screening'.",
                    related=f"application:{app2.id}",
                    read=True,
                    created_at=now - timedelta(days=6),
                )
            )

        session.add(
            ActivityLog(
                actor_user_id=dr_sharma.id,
                entity_type="Opportunity",
                entity_id=opp1.id,
                project_id=proj1.id,
                action="Opportunity published to ResearchBridge platform",
                timestamp=now - timedelta(days=14),
            )
        )
        session.add(
            ActivityLog(
                actor_user_id=aarav.id,
                entity_type="Application",
                entity_id=app1.id,
                project_id=proj1.id,
                action="Student submitted application with portfolio snapshot",
                timestamp=now - timedelta(days=12),
            )
        )
        session.add(
            ActivityLog(
                actor_user_id=dr_sharma.id,
                entity_type="Application",
                entity_id=app1.id,
                project_id=proj1.id,
                action="Faculty mentor approved student application",
                timestamp=now - timedelta(days=10),
            )
        )
        session.commit()

    return {
        "status": "success",
        "demo_password": DEMO_PASSWORD,
        "accounts": [
            {"role": "Administrator", "email": "admin@researchbridge.edu", "password": DEMO_PASSWORD, "name": "Dr. Vikram Seth"},
            {"role": "Coordinator", "email": "coordinator@ves.ac.in", "password": DEMO_PASSWORD, "name": "Prof. Ananya Iyer"},
            {"role": "Faculty (AI Lab Lead)", "email": "dr.sharma@ves.ac.in", "password": DEMO_PASSWORD, "name": "Dr. Rajesh Sharma"},
            {"role": "Faculty (Env Data)", "email": "prof.patel@ves.ac.in", "password": DEMO_PASSWORD, "name": "Prof. Sunita Patel"},
            {"role": "Student (Accepted in AI Lab)", "email": "aarav.mehta@ves.ac.in", "password": DEMO_PASSWORD, "name": "Aarav Mehta"},
            {"role": "Student (Shortlisted)", "email": "priya.nair@ves.ac.in", "password": DEMO_PASSWORD, "name": "Priya Nair"},
            {"role": "Student (Applicant)", "email": "rohan.deshmukh@ves.ac.in", "password": DEMO_PASSWORD, "name": "Rohan Deshmukh"},
        ],
    }


if __name__ == "__main__":
    result = seed_all()
    print("\n" + "=" * 70)
    print("RESEARCHBRIDGE DEMO DATABASE SEEDED SUCCESSFULLY")
    print("=" * 70)
    print(f"Demo Password for all accounts: {result['demo_password']}\n")
    print("DEMO ACCOUNTS READY TO SHOW:")
    for acc in result["accounts"]:
        print(f"  [{acc['role']:<26}] {acc['email']:<28} | Name: {acc['name']}")
    print("=" * 70 + "\n")

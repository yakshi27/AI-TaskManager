"""
Page Render Functions for Streamlit App
Contains all page rendering logic separated for maintainability
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, Any, List
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.export_utils import (
    export_schedule_csv, export_stats_csv, 
    create_download_button, export_report_txt, export_full_plan
)


def render_create_plan_page(goal_agent, planner_agent, memory):
    """Render the create plan page."""
    st.markdown('<h1 class="main-header">📝 Create Your Study Plan</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Let AI transform your goals into actionable plans</p>', unsafe_allow_html=True)
    
    # Examples
    with st.expander("💡 See Examples", expanded=False):
        st.markdown("""
        **Vague Goals** (AI figures it out):
        - "learn web development"
        - "get better at coding"
        - "prepare for interviews"
        
        **Specific Goals** (AI optimizes):
        - "Master Python in 30 days, 2 hours daily"
        - "AWS certification prep, 60 days, 3 hours/day"
        - "Learn React and build 3 projects in 45 days"
        """)
    
    # Input form
    with st.form("create_plan_form", clear_on_submit=False):
        st.markdown("### 🎯 Describe Your Learning Goal")
        
        goal_input = st.text_area(
            "What do you want to learn?",
            placeholder="Examples:\n• Learn Python programming in 30 days\n• Master machine learning fundamentals in 60 days, studying 2 hours daily\n• Prepare for AWS certification exam",
            height=150,
            help="Be as specific or vague as you like - our AI will figure it out!"
        )
        
        st.markdown("### ⚙️ Customization (Optional)")
        
        col1, col2 = st.columns(2)
        with col1:
            custom_days = st.number_input(
                "Duration (days)",
                min_value=0,
                max_value=365,
                value=0,
                help="Leave as 0 to let AI decide optimal duration"
            )
        
        with col2:
            custom_hours = st.number_input(
                "Daily study hours",
                min_value=0.0,
                max_value=12.0,
                value=0.0,
                step=0.5,
                help="Leave as 0 to let AI suggest realistic hours"
            )
        
        submitted = st.form_submit_button("🚀 Create My Study Plan", type="primary", use_container_width=True)
    
    if submitted:
        if not goal_input.strip():
            st.error("❌ Please enter your study goal")
            return
        
        with st.spinner("🤖 AI agents are working on your personalized plan..."):
            try:
                # Step 1: Parse goal
                with st.status("🎯 Analyzing your goal...", expanded=True) as status:
                    st.write("Goal Agent is understanding your requirements...")
                    parsed_goal = goal_agent.parse_goal(goal_input)
                    
                    # Override with custom values
                    if custom_days > 0:
                        parsed_goal['total_days'] = custom_days
                    if custom_hours > 0:
                        parsed_goal['hours_per_day'] = custom_hours
                    
                    st.write("✅ Goal analyzed successfully!")
                    status.update(label="✅ Goal Analysis Complete", state="complete")
                
                # Step 2: Create schedule
                with st.status("📅 Creating your personalized schedule...", expanded=True) as status:
                    st.write("Planner Agent is designing your learning path...")
                    schedule = planner_agent.create_schedule(parsed_goal)
                    st.write("✅ Schedule created successfully!")
                    status.update(label="✅ Schedule Creation Complete", state="complete")
                
                # Step 3: Save
                with st.status("💾 Saving your plan...", expanded=True) as status:
                    plan_data = {
                        "goal": goal_input,
                        "parsed_goal": parsed_goal,
                        "schedule": schedule
                    }
                    
                    if memory.save_plan(plan_data):
                        st.write("✅ Plan saved successfully!")
                        status.update(label="✅ Save Complete", state="complete")
                    else:
                        st.error("Failed to save plan")
                        return
                
                # Success!
                st.balloons()
                
                st.markdown("""
                <div class="success-box">
                    <h3>🎉 Your Study Plan is Ready!</h3>
                    <p>Your personalized learning journey has been created.</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Display summary
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📅 Duration", f"{parsed_goal['total_days']} days")
                with col2:
                    st.metric("⏰ Daily Hours", f"{parsed_goal['hours_per_day']} hours")
                with col3:
                    st.metric("📚 Topics", len(parsed_goal['topics']))
                
                st.markdown("### 🎯 Topics Covered")
                for i, topic in enumerate(parsed_goal['topics'], 1):
                    st.write(f"{i}. {topic}")
                
            except Exception as e:
                st.error(f"❌ Error creating plan: {e}")


def render_schedule_page(memory):
    """Render the schedule view page."""
    st.markdown('<h1 class="main-header">📅 Study Schedule</h1>', unsafe_allow_html=True)
    
    plan = memory.get_latest_plan()
    
    if not plan:
        st.warning("No study plan found. Create one first!")
        return
    
    schedule = plan.get('schedule', [])
    parsed_goal = plan.get('parsed_goal', {})
    
    # Plan header
    st.markdown(f"### 🎯 {plan.get('goal', 'Study Plan')}")
    st.caption(f"Created: {plan.get('created_at', 'N/A')[:10]}")
    
    # Filters
    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        status_filter = st.selectbox(
            "Filter by status",
            ["All", "Pending", "Completed"]
        )
    
    with col2:
        sort_by = st.selectbox(
            "Sort by",
            ["Day (Ascending)", "Day (Descending)", "Topic"]
        )
    
    # Filter schedule
    if status_filter == "Pending":
        filtered_schedule = [d for d in schedule if d.get("status") == "pending"]
    elif status_filter == "Completed":
        filtered_schedule = [d for d in schedule if d.get("status") == "done"]
    else:
        filtered_schedule = schedule
    
    # Sort
    if sort_by == "Day (Ascending)":
        filtered_schedule = sorted(filtered_schedule, key=lambda x: x.get('day', 0))
    elif sort_by == "Day (Descending)":
        filtered_schedule = sorted(filtered_schedule, key=lambda x: x.get('day', 0), reverse=True)
    elif sort_by == "Topic":
        filtered_schedule = sorted(filtered_schedule, key=lambda x: x.get('topic', ''))
    
    # Convert to DataFrame for display
    if filtered_schedule:
        df = pd.DataFrame(filtered_schedule)
        df['status_icon'] = df['status'].apply(lambda x: "✅" if x == "done" else "⏳")
        df_display = df[['day', 'topic', 'duration_hours', 'status_icon', 'notes']]
        df_display.columns = ['Day', 'Topic', 'Hours', 'Status', 'Notes']
        
        st.dataframe(
            df_display,
            use_container_width=True,
            height=400
        )
        
        # Export option
        csv = export_schedule_csv(filtered_schedule, plan.get('goal', ''))
        st.markdown(
            create_download_button(
                csv, 
                f"study_schedule_{datetime.now().strftime('%Y%m%d')}.csv",
                "Export Schedule as CSV"
            ),
            unsafe_allow_html=True
        )
    else:
        st.info("No tasks match the selected filter")


def render_mark_complete_page(task_manager, memory):
    """Render the mark complete page."""
    st.markdown('<h1 class="main-header">✅ Mark Day Complete</h1>', unsafe_allow_html=True)
    
    plan = memory.get_latest_plan()
    
    if not plan:
        st.warning("No study plan found. Create one first!")
        return
    
    schedule = plan.get('schedule', [])
    pending = [d for d in schedule if d.get("status") == "pending"]
    
    if not pending:
        st.success("🎉 Congratulations! All days are complete!")
        st.balloons()
        return
    
    # Show pending tasks
    st.markdown("### ⏳ Pending Tasks")
    
    # Quick complete - first 5 pending
    for day in pending[:5]:
        with st.container():
            col1, col2 = st.columns([4, 1])
            
            with col1:
                st.markdown(f"""
                **Day {day['day']}: {day['topic']}**  
                ⏰ {day['duration_hours']} hours  
                📝 {day['notes']}
                """)
            
            with col2:
                if st.button(f"✅ Complete", key=f"complete_{day['day']}"):
                    updated_schedule = task_manager.mark_day_complete(schedule, day['day'])
                    
                    if memory.update_plan_schedule(plan['id'], updated_schedule):
                        st.success(f"✅ Day {day['day']} marked as complete!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Failed to update schedule")
            
            st.markdown("---")
    
    if len(pending) > 5:
        st.info(f"... and {len(pending) - 5} more pending tasks")
    
    # Bulk complete
    st.markdown("### 🔢 Bulk Complete")
    
    with st.form("bulk_complete_form"):
        day_numbers_input = st.text_input(
            "Enter day numbers (comma-separated)",
            placeholder="e.g., 1, 2, 3"
        )
        
        if st.form_submit_button("✅ Mark Multiple Days Complete"):
            try:
                day_numbers = [int(d.strip()) for d in day_numbers_input.split(",") if d.strip()]
                
                updated_schedule = task_manager.mark_multiple_days_complete(schedule, day_numbers)
                
                if memory.update_plan_schedule(plan['id'], updated_schedule):
                    st.success(f"✅ Marked {len(day_numbers)} days as complete!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("Failed to update schedule")
                    
            except ValueError:
                st.error("Invalid day numbers. Use format: 1, 2, 3")


def render_analytics_page(memory):
    """Render the advanced analytics page."""
    st.markdown('<h1 class="main-header">📊 Advanced Analytics</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Deep insights into your learning journey</p>', unsafe_allow_html=True)
    
    plan = memory.get_latest_plan()
    
    if not plan:
        st.warning("No study plan found. Create one first!")
        return
    
    schedule = plan.get('schedule', [])
    stats = memory.get_plan_statistics(plan['id'])
    
    # Overview metrics
    st.markdown("### 📈 Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Days", stats['total_days'])
    with col2:
        st.metric("Completed", stats['completed_days'], f"{stats['progress_percentage']:.0f}%")
    with col3:
        st.metric("Pending", stats['pending_days'])
    with col4:
        st.metric("Total Hours", f"{stats['total_hours']:.1f}h")
    
    # Visualizations
    st.markdown("### 📊 Visualizations")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Progress", "🎯 Topics", "⏰ Time Analysis", "🔥 Streaks"])
    
    with tab1:
        # Cumulative hours chart
        from ui.app import create_cumulative_hours_chart
        fig = create_cumulative_hours_chart(schedule)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Complete some days to see progress chart")
    
    with tab2:
        # Topic distribution
        from ui.app import create_topic_distribution_chart
        fig = create_topic_distribution_chart(schedule)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        # Hours breakdown
        completed_tasks = [d for d in schedule if d.get('status') == 'done']
        pending_tasks = [d for d in schedule if d.get('status') == 'pending']
        
        fig = go.Figure(data=[
            go.Bar(name='Completed', x=['Hours'], y=[stats['completed_hours']], marker_color='#55efc4'),
            go.Bar(name='Remaining', x=['Hours'], y=[stats['total_hours'] - stats['completed_hours']], marker_color='#ffcccb')
        ])
        
        fig.update_layout(
            title='Study Hours Breakdown',
            yaxis_title='Hours',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        # Streak information
        from ui.app import get_streak_info
        streak_info = get_streak_info(schedule)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("🔥 Current Streak", f"{streak_info['current_streak']} days")
        with col2:
            st.metric("🏆 Best Streak", f"{streak_info['longest_streak']} days")
        
        if streak_info['last_study']:
            st.info(f"📚 Last studied: {streak_info['last_study']}")


def render_all_plans_page(memory):
    """Render all plans management page."""
    st.markdown('<h1 class="main-header">🎯 All Plans</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Manage all your study plans</p>', unsafe_allow_html=True)
    
    plans = memory.get_all_plans()
    
    if not plans:
        st.info("No plans found. Create your first plan!")
        return
    
    # Summary
    st.markdown(f"### 📊 You have {len(plans)} study plan(s)")
    
    # Display each plan
    for plan in plans:
        stats = memory.get_plan_statistics(plan['id'])
        
        with st.expander(f"📚 Plan #{plan['id']}: {plan.get('goal', 'N/A')[:50]}", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Progress", f"{stats['progress_percentage']:.0f}%")
                st.metric("Total Days", stats['total_days'])
            
            with col2:
                st.metric("Completed", stats['completed_days'])
                st.metric("Pending", stats['pending_days'])
            
            with col3:
                st.metric("Hours Done", f"{stats['completed_hours']:.1f}h")
                st.metric("Hours Left", f"{stats['total_hours'] - stats['completed_hours']:.1f}h")
            
            # Actions
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button(f"👁️ View", key=f"view_{plan['id']}"):
                    st.session_state.selected_plan = plan['id']
                    st.rerun()
            
            with col2:
                csv = export_full_plan(plan, stats)
                st.markdown(
                    create_download_button(
                        csv,
                        f"plan_{plan['id']}.csv",
                        "Export"
                    ),
                    unsafe_allow_html=True
                )
            
            with col3:
                if st.button(f"🗑️ Delete", key=f"delete_{plan['id']}"):
                    if memory.delete_plan(plan['id']):
                        st.success(f"Plan #{plan['id']} deleted")
                        st.rerun()


def render_export_page(memory, report_agent):
    """Render the export data page."""
    st.markdown('<h1 class="main-header">📥 Export Data</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Download your study data in various formats</p>', unsafe_allow_html=True)
    
    plan = memory.get_latest_plan()
    
    if not plan:
        st.warning("No study plan found. Create one first!")
        return
    
    schedule = plan.get('schedule', [])
    stats = memory.get_plan_statistics(plan['id'])
    
    st.markdown("### 📊 Available Exports")
    
    # Export options
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📅 Schedule Data")
        
        # CSV Export
        csv_schedule = export_schedule_csv(schedule, plan.get('goal', ''))
        st.markdown(
            create_download_button(
                csv_schedule,
                f"schedule_{datetime.now().strftime('%Y%m%d')}.csv",
                "Download Schedule (CSV)"
            ),
            unsafe_allow_html=True
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Statistics Export
        csv_stats = export_stats_csv(stats)
        st.markdown(
            create_download_button(
                csv_stats,
                f"statistics_{datetime.now().strftime('%Y%m%d')}.csv",
                "Download Statistics (CSV)"
            ),
            unsafe_allow_html=True
        )
    
    with col2:
        st.markdown("#### 📊 Reports")
        
        # Generate and export report
        if st.button("📝 Generate Report", type="primary"):
            with st.spinner("Generating report..."):
                report = report_agent.generate_report(schedule, use_ai=True)
                txt_report = export_report_txt(report, plan.get('goal', ''))
                
                st.markdown(
                    create_download_button(
                        txt_report,
                        f"report_{datetime.now().strftime('%Y%m%d')}.txt",
                        "Download Report (TXT)"
                    ),
                    unsafe_allow_html=True
                )
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Complete plan export
        csv_full = export_full_plan(plan, stats)
        st.markdown(
            create_download_button(
                csv_full,
                f"complete_plan_{datetime.now().strftime('%Y%m%d')}.csv",
                "Download Complete Plan (CSV)"
            ),
            unsafe_allow_html=True
        )
    
    # Preview
    st.markdown("### 👀 Data Preview")
    
    tab1, tab2 = st.tabs(["📅 Schedule", "📊 Statistics"])
    
    with tab1:
        df = pd.DataFrame(schedule)
        st.dataframe(df, use_container_width=True)
    
    with tab2:
        st.json(stats)
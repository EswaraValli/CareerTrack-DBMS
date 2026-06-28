"""
Performance Benchmarking Script for CareerTrack PMS
SubTask 4 & 5: SQL Indexing and Query Optimization

This script measures API performance and SQL query execution times
before and after applying indexes.
"""

import time
import sqlite3
import json
from datetime import datetime
import os

class PerformanceBenchmark:
    def __init__(self, db_path='careertrack.db'):
        self.db_path = db_path
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'queries': []
        }
    
    def measure_query(self, query_name, sql_query, params=None, description=""):
        """
        Measure execution time and get EXPLAIN QUERY PLAN for a SQL query
        
        Args:
            query_name: Name of the query being tested
            sql_query: The SQL query to execute
            params: Query parameters (tuple)
            description: Description of what this query does
        
        Returns:
            dict: Performance metrics including time and execution plan
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get EXPLAIN QUERY PLAN
        explain_query = f"EXPLAIN QUERY PLAN {sql_query}"
        cursor.execute(explain_query, params or ())
        explain_plan = cursor.fetchall()
        
        # Measure execution time (run multiple times for accuracy)
        execution_times = []
        num_runs = 10
        
        for _ in range(num_runs):
            start_time = time.perf_counter()
            cursor.execute(sql_query, params or ())
            results = cursor.fetchall()
            end_time = time.perf_counter()
            execution_times.append((end_time - start_time) * 1000)  # Convert to ms
        
        avg_time = sum(execution_times) / len(execution_times)
        min_time = min(execution_times)
        max_time = max(execution_times)
        
        conn.close()
        
        result = {
            'query_name': query_name,
            'description': description,
            'sql': sql_query,
            'avg_time_ms': round(avg_time, 3),
            'min_time_ms': round(min_time, 3),
            'max_time_ms': round(max_time, 3),
            'num_runs': num_runs,
            'explain_plan': [
                {
                    'id': row[0],
                    'parent': row[1],
                    'detail': row[3]
                } for row in explain_plan
            ],
            'row_count': len(results)
        }
        
        self.results['queries'].append(result)
        return result
    
    def run_all_benchmarks(self):
        """Run all performance benchmarks for key queries"""
        
        print("=" * 80)
        print("PERFORMANCE BENCHMARKING - CareerTrack PMS")
        print("=" * 80)
        print(f"Database: {self.db_path}")
        print(f"Timestamp: {self.results['timestamp']}")
        print()
        
        # Test 1: Get all students (Member Portfolio)
        print("1. Testing: Get All Students (Member Portfolio)")
        result = self.measure_query(
            "get_all_students",
            """
            SELECT s.*, d.DeptName 
            FROM Student s
            LEFT JOIN Department d ON s.DeptID = d.DeptID
            ORDER BY s.CGPA DESC
            """,
            description="Fetch all students with department info, ordered by CGPA"
        )
        self.print_result(result)
        
        # Test 2: Get eligible jobs for a student
        print("\n2. Testing: Get Eligible Jobs for Student (CGPA-based filtering)")
        result = self.measure_query(
            "get_eligible_jobs",
            """
            SELECT j.*, c.CompanyName, pd.DriveName
            FROM JobPosting j
            LEFT JOIN Company c ON j.CompanyID = c.CompanyID
            LEFT JOIN PlacementDrive pd ON j.DriveID = pd.DriveID
            WHERE j.MinCGPA <= 8.5
            AND (j.Deadline IS NULL OR j.Deadline >= DATE('now'))
            ORDER BY j.PostDate DESC
            """,
            description="Find jobs eligible for student with CGPA 8.5"
        )
        self.print_result(result)
        
        # Test 3: Get student applications with job details
        print("\n3. Testing: Get Student Applications")
        result = self.measure_query(
            "get_student_applications",
            """
            SELECT a.*, s.Name as StudentName, j.RoleTitle, c.CompanyName, j.Package_LPA
            FROM Application a
            JOIN Student s ON a.StudentID = s.StudentID
            JOIN JobPosting j ON a.JobID = j.JobID
            JOIN Company c ON j.CompanyID = c.CompanyID
            WHERE a.StudentID = 1
            ORDER BY a.ApplyDate DESC
            """,
            description="Get all applications for a specific student"
        )
        self.print_result(result)
        
        # Test 4: Get job applicants (for company/admin view)
        print("\n4. Testing: Get Job Applicants")
        result = self.measure_query(
            "get_job_applicants",
            """
            SELECT a.*, s.Name, s.Email, s.CGPA, s.GraduationYear, d.DeptName
            FROM Application a
            JOIN Student s ON a.StudentID = s.StudentID
            LEFT JOIN Department d ON s.DeptID = d.DeptID
            WHERE a.JobID = 1
            ORDER BY s.CGPA DESC, a.ApplyDate
            """,
            description="Get all applicants for a specific job, ordered by CGPA"
        )
        self.print_result(result)
        
        # Test 5: Placement statistics query
        print("\n5. Testing: Placement Statistics (Analytics)")
        result = self.measure_query(
            "placement_statistics",
            """
            SELECT d.DeptName, 
                   COUNT(DISTINCT s.StudentID) as total_students,
                   COUNT(DISTINCT CASE WHEN s.IsPlaced = 1 THEN s.StudentID END) as placed_students
            FROM Department d
            LEFT JOIN Student s ON d.DeptID = s.DeptID
            GROUP BY d.DeptID
            """,
            description="Calculate placement statistics by department"
        )
        self.print_result(result)
        
        # Test 6: Search students by CGPA range
        print("\n6. Testing: Search Students by CGPA Range")
        result = self.measure_query(
            "search_by_cgpa",
            """
            SELECT s.*, d.DeptName
            FROM Student s
            LEFT JOIN Department d ON s.DeptID = d.DeptID
            WHERE s.CGPA >= 8.0 AND s.CGPA <= 9.0
            ORDER BY s.CGPA DESC
            """,
            description="Find students with CGPA between 8.0 and 9.0"
        )
        self.print_result(result)
        
        # Test 7: Get student with skills
        print("\n7. Testing: Get Student Profile with Skills")
        result = self.measure_query(
            "get_student_with_skills",
            """
            SELECT s.*, d.DeptName,
                   GROUP_CONCAT(sk.SkillName || ' (' || ss.ProficiencyLevel || ')') as skills
            FROM Student s
            LEFT JOIN Department d ON s.DeptID = d.DeptID
            LEFT JOIN StudentSkill ss ON s.StudentID = ss.StudentID
            LEFT JOIN Skill sk ON ss.SkillID = sk.SkillID
            WHERE s.StudentID = 1
            GROUP BY s.StudentID
            """,
            description="Get complete student profile with all skills"
        )
        self.print_result(result)
        
        # Test 8: Company job postings
        print("\n8. Testing: Get Company Job Postings")
        result = self.measure_query(
            "company_jobs",
            """
            SELECT j.*, COUNT(a.AppID) as application_count
            FROM JobPosting j
            LEFT JOIN Application a ON j.JobID = a.JobID
            WHERE j.CompanyID = 1
            GROUP BY j.JobID
            ORDER BY j.PostDate DESC
            """,
            description="Get all jobs posted by a company with application counts"
        )
        self.print_result(result)
        
        print("\n" + "=" * 80)
        print("BENCHMARK COMPLETE")
        print("=" * 80)
        
        return self.results
    
    def print_result(self, result):
        """Print formatted benchmark result"""
        print(f"   Query: {result['query_name']}")
        print(f"   Avg Time: {result['avg_time_ms']:.3f} ms")
        print(f"   Min Time: {result['min_time_ms']:.3f} ms")
        print(f"   Max Time: {result['max_time_ms']:.3f} ms")
        print(f"   Rows: {result['row_count']}")
        print(f"   Execution Plan:")
        for plan in result['explain_plan']:
            print(f"      {plan['detail']}")
    
    def save_results(self, filename):
        """Save benchmark results to JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n✓ Results saved to: {filename}")
    
    def compare_with_previous(self, previous_file):
        """Compare current results with previous benchmark"""
        if not os.path.exists(previous_file):
            print(f"No previous benchmark found at {previous_file}")
            return
        
        with open(previous_file, 'r') as f:
            previous = json.load(f)
        
        print("\n" + "=" * 80)
        print("PERFORMANCE COMPARISON")
        print("=" * 80)
        
        print(f"\nPrevious: {previous['timestamp']}")
        print(f"Current:  {self.results['timestamp']}")
        print()
        
        # Create lookup for previous results
        prev_dict = {q['query_name']: q for q in previous['queries']}
        
        improvements = []
        
        for current_query in self.results['queries']:
            name = current_query['query_name']
            if name in prev_dict:
                prev_query = prev_dict[name]
                
                current_time = current_query['avg_time_ms']
                prev_time = prev_query['avg_time_ms']
                
                diff = current_time - prev_time
                percent_change = ((current_time - prev_time) / prev_time) * 100
                
                improvements.append({
                    'name': name,
                    'prev_time': prev_time,
                    'current_time': current_time,
                    'diff': diff,
                    'percent_change': percent_change
                })
                
                status = "🚀 FASTER" if diff < 0 else "⚠️ SLOWER"
                print(f"{status} {name}")
                print(f"   Before: {prev_time:.3f} ms")
                print(f"   After:  {current_time:.3f} ms")
                print(f"   Change: {diff:+.3f} ms ({percent_change:+.1f}%)")
                print()
        
        # Summary
        avg_improvement = sum(imp['percent_change'] for imp in improvements) / len(improvements)
        faster_count = sum(1 for imp in improvements if imp['diff'] < 0)
        
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total Queries: {len(improvements)}")
        print(f"Faster: {faster_count}")
        print(f"Slower: {len(improvements) - faster_count}")
        print(f"Average Performance Change: {avg_improvement:+.1f}%")
        print()


if __name__ == "__main__":
    import sys
    
    # Run benchmark
    benchmark = PerformanceBenchmark()
    results = benchmark.run_all_benchmarks()
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if len(sys.argv) > 1 and sys.argv[1] == 'before':
        filename = 'benchmark_before_indexes.json'
        print("\n📊 Running BEFORE indexes benchmark...")
    elif len(sys.argv) > 1 and sys.argv[1] == 'after':
        filename = 'benchmark_after_indexes.json'
        print("\n📊 Running AFTER indexes benchmark...")
        
        # Compare with before
        if os.path.exists('benchmark_before_indexes.json'):
            benchmark.compare_with_previous('benchmark_before_indexes.json')
    else:
        filename = f'benchmark_{timestamp}.json'
    
    benchmark.save_results(filename)
    
    print("\n" + "=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    if 'before' in filename:
        print("1. Now apply indexes: Check sql/indexes.sql")
        print("2. Run: python benchmark.py after")
        print("3. Compare the results!")
    elif 'after' in filename:
        print("✅ Benchmarking complete!")
        print("📊 Check the comparison results above")
        print("📄 Generate report: python generate_report.py")
    else:
        print("Run with 'before' or 'after' argument:")
        print("  python benchmark.py before")
        print("  python benchmark.py after")

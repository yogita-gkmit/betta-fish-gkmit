
import os
import json

class FileCountBaseline:
    def __init__(self):
        self.baseline_file = 'logs/report_baseline.json'
        
    def _load_baseline(self):
        try:
            if os.path.exists(self.baseline_file):
                with open(self.baseline_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Failed to load baseline: {e}")
        return {}

    def check_new_files(self, directories):
        self.baseline_data = self._load_baseline()
        print(f"Loaded Baseline: {self.baseline_data}")
        
        current_counts = {}
        new_files_found = {}
        all_have_new = True
        
        for engine, directory in directories.items():
            if os.path.exists(directory):
                md_files = [f for f in os.listdir(directory) if f.endswith('.md')]
                current_counts[engine] = len(md_files)
                baseline_count = self.baseline_data.get(engine, 0)
                
                print(f"Engine {engine}: Current={current_counts[engine]}, Baseline={baseline_count}")
                
                if current_counts[engine] > baseline_count:
                    new_files_found[engine] = current_counts[engine] - baseline_count
                else:
                    new_files_found[engine] = 0
                    all_have_new = False
            else:
                print(f"Engine {engine}: Directory not found!")
                current_counts[engine] = 0
                new_files_found[engine] = 0
                all_have_new = False
        
        return {
            'ready': all_have_new,
            'baseline_counts': self.baseline_data,
            'current_counts': current_counts,
            'new_files_found': new_files_found,
            'missing_engines': [engine for engine, count in new_files_found.items() if count == 0]
        }

def check_input_files(directories, forum_log_path):
    fc = FileCountBaseline()
    check_result = fc.check_new_files(directories)
    
    forum_ready = os.path.exists(forum_log_path)
    print(f"Forum Log Exists: {forum_ready} ({forum_log_path})")
    
    all_engines_have_files = all(count > 0 for count in check_result['current_counts'].values())
    files_ready = check_result['ready'] or all_engines_have_files
    
    print(f"Check Result Ready (New Files): {check_result['ready']}")
    print(f"All Engines Have Files (>0): {all_engines_have_files}")
    print(f"FINAL Files Ready: {files_ready}")
    print(f"FINAL Result (Ready & Forum): {files_ready and forum_ready}")

if __name__ == "__main__":
    dirs = {
        'insight': 'insight_engine_streamlit_reports',
        'media': 'media_engine_streamlit_reports',
        'query': 'query_engine_streamlit_reports'
    }
    log = 'logs/forum.log'
    print("--- Verifying Report Readiness ---")
    check_input_files(dirs, log)
    print("----------------------------------")

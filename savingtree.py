import joblib
import os

def save_points_and_tree(object_id, sampled_points, tree, save_dir="data"):
    os.makedirs(save_dir, exist_ok=True)
    path = os.path.join(save_dir, f"{object_id}_points.pkl")
    joblib.dump({'points': sampled_points, 'tree': tree}, path)
    return path

def load_points_and_tree(path):
    data = joblib.load(path)
    return data['points'], data['tree']


def load_and_delete_points_and_tree(path):
    data = joblib.load(path)
    os.remove(path)  # ✅ Delete file immediately after loading
    return data['points'], data['tree']



def delete_all_cached_kdtrees(save_dir="data"):
    if not os.path.exists(save_dir):
        print(f"No such directory: {save_dir}")
        return

    for filename in os.listdir(save_dir):
        file_path = os.path.join(save_dir, filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")
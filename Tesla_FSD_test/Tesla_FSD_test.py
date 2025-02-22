import numpy as np
import cv2
import requests
import os
import time
from skimage.util import random_noise

# Fetch real weather data
def fetch_real_weather():
    api_key = "da7e82ef806d207f95157b286978f5e8"  # Replace with your OpenWeatherMap API key
    url = f"http://api.openweathermap.org/data/2.5/weather?q=SanFrancisco&appid={api_key}&units=metric"
    try:
        response = requests.get(url).json()
        condition = response["weather"][0]["main"].lower()
        visibility = response.get("visibility", 10000) / 1000  # m to km
        temp = response["main"]["temp"]
        if "rain" in condition:
            condition = "rain"
        elif "fog" in condition or "mist" in condition:
            condition = "fog"
        elif "snow" in condition:
            condition = "snow"
        else:
            condition = "clear"
    except Exception as e:
        print(f"API error: {e}. Using fallback data.")
        condition, visibility, temp = "fog", 0.5, 2
    print(f"Starlink Alert: {condition.capitalize()} detected, Visibility: {visibility} km, Temp: {temp}°C")
    return condition, visibility, temp

# Current FSD detection (problem)
def current_fsd_detection(visibility):
    base_accuracy = 90
    if visibility < 1:
        accuracy = base_accuracy * 0.25
    elif visibility < 3:
        accuracy = base_accuracy * 0.5
    else:
        accuracy = base_accuracy
    return accuracy + np.random.normal(0, 7)

# IR-enhanced FSD detection (solution)
def ir_fsd_detection(visibility):
    base_accuracy = 85
    if visibility < 3:
        accuracy = base_accuracy * 0.9
    else:
        accuracy = base_accuracy
    return accuracy + np.random.normal(0, 3)

# FSD decisions
def fsd_decision(current_acc, ir_acc, visibility):
    problem_decision = "Disengage FSD" if current_acc < 50 else "Proceed with caution"
    solution_decision = "Slow to 20 mph, use IR" if visibility < 1 else "Maintain speed, monitor with IR"
    return problem_decision, solution_decision

# Generate video frames
def generate_video_frames(condition, temp, visibility, current_acc, ir_acc, problem_decision, solution_decision):
    os.makedirs("outputs/frames", exist_ok=True)
    frame_width, frame_height = 800, 400
    frames = []
    
    # Intro frame
    intro = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
    cv2.putText(intro, "FSD WeatherSync: Problem vs Solution", (100, 180), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(intro, f"Weather: {condition.capitalize()}, Vis: {visibility} km", (100, 230), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
    for _ in range(10):  # 2 seconds at 5 fps
        frames.append(intro)
    
    # Animation frames
    for i in range(30):  # 6 seconds at 5 fps
        frame = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
        x_shift = 50 + i * 3  # Smoother motion
        
        # Problem side (left: foggy RGB)
        problem_img = np.ones((300, 400), dtype=np.uint8) * 70
        if current_acc > 50:  # Faint objects
            cv2.rectangle(problem_img, (150, 80), (200, 200), (100), -1)
            cv2.rectangle(problem_img, (x_shift, 180), (x_shift + 100, 230), (100), -1)
            cv2.rectangle(problem_img, (x_shift + 30, 150), (x_shift + 80, 180), (100), -1)
            cv2.circle(problem_img, (x_shift + 20, 230), 15, (90), -1)
            cv2.circle(problem_img, (x_shift + 80, 230), 15, (90), -1)
        problem_img = random_noise(problem_img, mode="gaussian", var=0.05) * 255
        problem_img = np.clip(problem_img, 0, 255).astype(np.uint8)
        problem_img_colored = cv2.cvtColor(problem_img, cv2.COLOR_GRAY2BGR)
        cv2.putText(problem_img_colored, "Current FSD (Problem)", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(problem_img_colored, f"Accuracy: {current_acc:.1f}%", (10, 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(problem_img_colored, f"Decision: {problem_decision}", (10, 90), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        if i > 15 and current_acc < 50:
            cv2.putText(problem_img_colored, "FSD Disengaged", (100, 200), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        # Solution side (right: IR heatmap)
        solution_img = np.ones((300, 400), dtype=np.uint8) * max(30, min(70, 50 - int(temp * 2)))
        cv2.rectangle(solution_img, (150, 80), (200, 200), (255), -1)
        cv2.rectangle(solution_img, (x_shift, 180), (x_shift + 100, 230), (255), -1)
        cv2.rectangle(solution_img, (x_shift + 30, 150), (x_shift + 80, 180), (255), -1)
        cv2.circle(solution_img, (x_shift + 20, 230), 15, (200), -1)
        cv2.circle(solution_img, (x_shift + 80, 230), 15, (200), -1)
        cv2.putText(solution_img, "T", (x_shift + 45, 165), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255), 2)  # Tesla logo
        if condition in ["fog", "rain"]:
            solution_img = random_noise(solution_img, mode="gaussian", var=0.03) * 255
        solution_img = cv2.applyColorMap(np.clip(solution_img, 0, 255).astype(np.uint8), cv2.COLORMAP_JET)
        cv2.putText(solution_img, "WeatherSync IR (Solution)", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(solution_img, f"Accuracy: {ir_acc:.1f}%", (10, 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(solution_img, f"Decision: {solution_decision}", (10, 90), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.putText(solution_img, "Tesla", (x_shift, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(solution_img, "Pedestrian", (150, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Combine
        frame[50:350, 0:400] = problem_img_colored
        frame[50:350, 400:800] = solution_img
        cv2.imwrite(f"outputs/frames/frame_{i}.png", frame)
        frames.append(frame)
    
    # Write video
    out = cv2.VideoWriter("outputs/ir_detection.mp4", cv2.VideoWriter_fourcc(*"mp4v"), 5, (frame_width, frame_height))
    for frame in frames:
        out.write(frame)
    out.release()
    print("Video simulation saved as 'outputs/ir_detection.mp4'")

# Main simulation
def run_fsd_weathersync():
    os.makedirs("outputs", exist_ok=True)
    
    # Fetch weather
    condition, visibility, temp = fetch_real_weather()
    
    # Simulate detections
    current_acc = current_fsd_detection(visibility)
    ir_acc = ir_fsd_detection(visibility)
    
    # Decisions
    problem_decision, solution_decision = fsd_decision(current_acc, ir_acc, visibility)
    
    # Report
    report = (
        f"FSD WeatherSync Simulation\n"
        f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Weather: {condition.capitalize()}, Visibility: {visibility} km, Temp: {temp}°C\n"
        f"\nProblem (Current FSD):\n"
        f"Accuracy: {current_acc:.1f}% - Struggles in {condition}.\n"
        f"Decision: {problem_decision}\n"
        f"\nSolution (WeatherSync with IR):\n"
        f"Accuracy: {ir_acc:.1f}% - Reliable with IR.\n"
        f"Decision: {solution_decision}\n"
    )
    print(report)
    with open("outputs/report.txt", "w") as f:
        f.write(report)
    
    # Generate video if bad weather
    if condition != "clear":
        generate_video_frames(condition, temp, visibility, current_acc, ir_acc, problem_decision, solution_decision)

if __name__ == "__main__":
    run_fsd_weathersync()

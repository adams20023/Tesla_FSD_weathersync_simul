import numpy as np
import cv2
import pandas as pd
import matplotlib.pyplot as plt
from skimage.util import random_noise
import requests
import os
import time

# Fetch real weather data
def fetch_real_weather():
    api_key = "YOUR_API_KEY_HERE"  # Replace with your OpenWeatherMap API key
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
        condition, visibility, temp = "fog", 0.5, 2  # Fallback
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

# Generate video frames for problem vs. solution
def generate_video_frames(condition, temp, current_acc, ir_acc, problem_decision, solution_decision):
    os.makedirs("outputs/frames", exist_ok=True)
    frame_width, frame_height = 800, 400  # Wider for side-by-side
    frames = []
    
    for i in range(20):  # 20 frames ~ 10 seconds at 2 fps
        # Split frame: Left (problem), Right (solution)
        frame = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
        
        # Problem side (left: RGB camera in fog)
        problem_img = np.ones((300, 400), dtype=np.uint8) * 50  # Foggy gray
        x_shift = 50 + i * 5  # Tesla moves right
        if current_acc > 50:  # Barely visible if accuracy is decent
            cv2.rectangle(problem_img, (150, 80), (200, 200), (100), -1)  # Faint pedestrian
            cv2.rectangle(problem_img, (x_shift, 180), (x_shift + 100, 230), (100), -1)  # Faint Tesla
        problem_img = random_noise(problem_img, mode="gaussian", var=0.05) * 255  # Updated noise
        problem_img = np.clip(problem_img, 0, 255).astype(np.uint8)
        problem_img_colored = cv2.cvtColor(problem_img, cv2.COLOR_GRAY2BGR)
        cv2.putText(problem_img_colored, "Current FSD (Problem)", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(problem_img_colored, f"Accuracy: {current_acc:.1f}%", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(problem_img_colored, f"Decision: {problem_decision}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
        
        # Solution side (right: IR camera)
        solution_img = np.ones((300, 400), dtype=np.uint8) * max(30, min(70, 50 - int(temp * 2)))
        cv2.rectangle(solution_img, (150, 80), (200, 200), (255), -1)  # Clear pedestrian
        cv2.rectangle(solution_img, (x_shift, 180), (x_shift + 100, 230), (255), -1)  # Clear Tesla
        cv2.rectangle(solution_img, (x_shift + 30, 150), (x_shift + 80, 180), (255), -1)
        cv2.circle(solution_img, (x_shift + 20, 230), 15, (200), -1)
        cv2.circle(solution_img, (x_shift + 80, 230), 15, (200), -1)
        if condition in ["fog", "rain"]:
            solution_img = random_noise(solution_img, mode="gaussian", var=0.03) * 255  # Updated noise
        solution_img = cv2.applyColorMap(np.clip(solution_img, 0, 255).astype(np.uint8), cv2.COLORMAP_JET)
        cv2.putText(solution_img, "WeatherSync IR (Solution)", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(solution_img, f"Accuracy: {ir_acc:.1f}%", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(solution_img, f"Decision: {solution_decision}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # Combine side-by-side
        frame[50:350, 0:400] = problem_img_colored
        frame[50:350, 400:800] = solution_img
        cv2.imwrite(f"outputs/frames/frame_{i}.png", frame)
        frames.append(frame)
    
    # Create video
    out = cv2.VideoWriter("outputs/ir_detection.mp4", cv2.VideoWriter_fourcc(*"mp4v"), 2, (frame_width, frame_height))
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
        generate_video_frames(condition, temp, current_acc, ir_acc, problem_decision, solution_decision)
    
    # Accuracy plot
    plt.figure(figsize=(10, 6))
    bars = plt.bar(["Current FSD (Problem)", "WeatherSync IR (Solution)"], 
                   [current_acc, ir_acc], color=["gray", "green"])
    plt.title(f"FSD Performance in {condition.capitalize()} (Vis: {visibility} km)")
    plt.ylabel("Accuracy (%)")
    plt.ylim(0, 100)
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + 2, f"{yval:.1f}%", ha="center")
    plt.savefig("outputs/accuracy_plot.png")
    plt.close()
    print("Accuracy plot saved as 'outputs/accuracy_plot.png'")

if __name__ == "__main__":
    run_fsd_weathersync()

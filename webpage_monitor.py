import argparse
import subprocess
import time
import traceback

import cv2
import numpy as np
from PIL import Image, ImageDraw
from selenium import webdriver
from selenium.webdriver import ChromeOptions


class WebpageMonitor:
    def __init__(self, executable_path='./chromedriver'):
        self.driver = self.create_driver(executable_path)

    @staticmethod
    def create_driver(exec_path):
        """Create a ChromeDriver instance."""
        options = ChromeOptions()
        options.add_argument('--headless')
        return webdriver.Chrome(executable_path=exec_path, options=options)

    def url_to_img(self, url, resolution=(1920, 1080), full_page=True):
        """Take a screenshot of a webpage and save it to a file."""

        # Load the webpage
        self.driver.get(url)

        if full_page:
            # Get page body height
            body_height = self.driver.execute_script('return document.body.scrollHeight')
            # Set the resolution
            self.driver.set_window_size(resolution[0], body_height)
        else:
            # Set the resolution
            self.driver.set_window_size(resolution[0], resolution[1])

        # Save to binary png
        png = self.driver.get_screenshot_as_png()

        # Load binary png into OpenCV
        img = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_UNCHANGED)

        return img


    def find_differences(self, img1, img2, area=None) -> list:
        """Find the different areas between two images."""

        # Convert the images to grayscale
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

        if area:
            # Crop the images to the area
            gray1 = gray1[area[1]:area[1] + area[3], area[0]:area[0] + area[2]]
            gray2 = gray2[area[1]:area[1] + area[3], area[0]:area[0] + area[2]]

        # Find the differences between the two images
        diff = cv2.subtract(gray1, gray2)

        # Find the contours
        contours, _ = cv2.findContours(diff, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Convert the contours to bounding boxes
        boundingBoxes = [cv2.boundingRect(c) for c in contours]

        # Group the bounding boxes uysing groupRectangles from OpenCV2
        groupedBoundingBoxes, _ = cv2.groupRectangles(boundingBoxes, 0, 1)

        # Convert coordinates to original image coordinates
        if area:
            groupedBoundingBoxes = [(x + area[0], y + area[1], w, h) for (x, y, w, h) in groupedBoundingBoxes]
        
        return groupedBoundingBoxes

    def draw_differences(self, img, diffs):
        """Draw the differences between two images on the second image."""

        # Convert the OpenCV image to a PIL image but change it to RGB first
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)

        # Convert img2 to an image with alpha channel
        img.putalpha(255)

        # Create a transparent overlay
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))

        # Create a drawing context
        draw = ImageDraw.Draw(overlay)

        # Convert different_areas to Pillow coordinates
        diffs = [(x, y, x + w, y + h) for (x, y, w, h) in diffs]

        # Add 5 pixel padding to the areas
        diffs = [(x - 5, y - 5, x2 + 5, y2 + 5) for (x, y, x2, y2) in diffs]

        for area in diffs:
            draw.rectangle(area, fill=(0, 255, 0, 50))

        # Add the overlay to the second image
        img = Image.alpha_composite(img, overlay)

        return img


    def compare_webpages(self, url1, url2):
        """Compare two webpages and return the differences. Highlight the differences in red"""

        # Take screenshots of both urls
        img1 = self.url_to_img(url1)
        img2 = self.url_to_img(url2)

        # Find the different areas
        differences = self.find_differences(img1, img2, area=(1500,100,300,600))

        # Draw the differences on the second image
        img2 = self.draw_differences(img1, img2, differences)

        # Save the image
        img2.save('differences.png')

        # Return the image
        return img2


    def monitor_url_for_changes(self, url, interval=5):
        """Monitor a url for differences in an infinite loop."""
        # Take a screenshot of the url
        img1 = self.url_to_img(url)

        while True:
            try:
                # Take another screenshot of the url
                img2 = self.url_to_img(url)

                # Find the different areas
                differences = self.find_differences(img1, img2)

                # If there are differences, draw them on the second image
                if any(differences):
                    img2 = self.draw_differences(img2, differences)

                    # Save the image
                    img2.save('differences.png')

                    # Load image in explorer
                    subprocess.run(['open', 'differences.png'], check=True)

                # Set img2 to img1
                img1 = img2.copy()

                # Wait for interval
                time.sleep(interval)

            except Exception:
                print("An error occurred. Traceback:")
                print(traceback.format_exc())

            finally:
                del img2  # delete the second image to save memory
                self.driver.quit()  # close the browser instance once you're done with it
                break


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument('url', type=str, help="URL to monitor for changes.")
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_arguments()

    monitor = WebpageMonitor()
    monitor.monitor_url_for_changes(args.url)
/**
 * Compensation Click Quiz Component
 * Renders a static skeleton frame and handles click-based answer validation
 *
 * Usage:
 *   CompensationClick.init(container, question)
 */

(function (window) {
  "use strict";

  // Reuse constants from skeleton_player.js
  const SVG_WIDTH = 400;
  const SVG_HEIGHT = 500;

  // Colors for the skeleton (using "bad" variant to show compensation)
  const COLORS = {
    bone: "#C94A4A",
    joint: "#C94A4A",
    jointFill: "#F5D6D6",
  };

  // Bone connections (same as skeleton_player.js)
  const BONES = [
    ["left_shoulder", "right_shoulder"],
    ["left_hip", "right_hip"],
    ["left_shoulder", "left_hip"],
    ["right_shoulder", "right_hip"],
    ["_neck_midpoint", "nose"],
    ["left_shoulder", "left_elbow"],
    ["left_elbow", "left_wrist"],
    ["right_shoulder", "right_elbow"],
    ["right_elbow", "right_wrist"],
    ["left_hip", "left_knee"],
    ["left_knee", "left_ankle"],
    ["left_ankle", "left_heel"],
    ["right_hip", "right_knee"],
    ["right_knee", "right_ankle"],
    ["right_ankle", "right_heel"],
  ];

  class CompensationClick {
    constructor(container, question) {
      this.container = container;
      this.question = question;
      this.data = null;
      this.attempts = 0;
      this.maxAttempts = 2;
      this.isCorrect = false;
      this.isComplete = false;
      this.clickedX = null;
      this.clickedY = null;
      this.elements = {};

      this.init();
    }

    async init() {
      this.render();
      await this.loadSkeletonData();
      if (this.data) {
        this.drawFrame();
        this.setupClickHandler();
      }
    }

    render() {
      this.container.innerHTML = `
        <div class="compensation-click-wrapper">
          <div class="skeleton-canvas-container">
            <svg class="compensation-svg" viewBox="0 0 ${SVG_WIDTH} ${SVG_HEIGHT}" preserveAspectRatio="xMidYMid meet">
              <g class="skeleton-bones"></g>
              <g class="skeleton-joints"></g>
              <g class="click-feedback-layer"></g>
              <rect class="click-capture" x="0" y="0" width="${SVG_WIDTH}" height="${SVG_HEIGHT}" fill="transparent" style="cursor: crosshair;"></rect>
            </svg>
          </div>
          <div class="feedback-area">
            <div class="feedback-message"></div>
            <div class="hint-callout" style="display: none;"></div>
            <div class="explanation-box" style="display: none;"></div>
          </div>
        </div>
      `;

      this.elements.svg = this.container.querySelector(".compensation-svg");
      this.elements.bonesGroup = this.container.querySelector(".skeleton-bones");
      this.elements.jointsGroup = this.container.querySelector(".skeleton-joints");
      this.elements.feedbackLayer = this.container.querySelector(".click-feedback-layer");
      this.elements.clickCapture = this.container.querySelector(".click-capture");
      this.elements.feedbackMessage = this.container.querySelector(".feedback-message");
      this.elements.hintCallout = this.container.querySelector(".hint-callout");
      this.elements.explanationBox = this.container.querySelector(".explanation-box");
      this.elements.canvasContainer = this.container.querySelector(".skeleton-canvas-container");
    }

    async loadSkeletonData() {
      const skeletonPath = `/static/skeletons/${this.question.skeleton}`;
      try {
        const response = await fetch(skeletonPath);
        if (!response.ok) {
          throw new Error(`Failed to load: ${response.status}`);
        }
        this.data = await response.json();
      } catch (error) {
        console.error("CompensationClick: Failed to load skeleton data", error);
        this.container.innerHTML = `
          <div class="skeleton-error">
            <p>Skeleton data not available</p>
            <p class="text-muted small">Could not load ${this.question.skeleton}</p>
          </div>
        `;
      }
    }

    getJointPosition(joints, name) {
      if (name === "_neck_midpoint") {
        const ls = joints["left_shoulder"];
        const rs = joints["right_shoulder"];
        if (ls && rs) {
          return [(ls[0] + rs[0]) / 2, (ls[1] + rs[1]) / 2];
        }
        return null;
      }
      return joints[name] || null;
    }

    toSvgCoords(normalizedPos) {
      if (!normalizedPos) return null;
      return [normalizedPos[0] * SVG_WIDTH, normalizedPos[1] * SVG_HEIGHT];
    }

    toNormalizedCoords(svgX, svgY) {
      return [svgX / SVG_WIDTH, svgY / SVG_HEIGHT];
    }

    drawFrame() {
      const frameIndex = this.question.frame_index || 0;
      if (!this.data || frameIndex >= this.data.frames.length) {
        console.error("Invalid frame index:", frameIndex);
        return;
      }

      const frame = this.data.frames[frameIndex];
      const joints = frame.joints;

      // Clear previous content
      this.elements.bonesGroup.innerHTML = "";
      this.elements.jointsGroup.innerHTML = "";

      // Draw bones
      for (const [from, to] of BONES) {
        const fromPos = this.toSvgCoords(this.getJointPosition(joints, from));
        const toPos = this.toSvgCoords(this.getJointPosition(joints, to));

        if (fromPos && toPos) {
          const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
          line.setAttribute("x1", fromPos[0]);
          line.setAttribute("y1", fromPos[1]);
          line.setAttribute("x2", toPos[0]);
          line.setAttribute("y2", toPos[1]);
          line.setAttribute("stroke", COLORS.bone);
          line.setAttribute("stroke-width", "3");
          line.setAttribute("stroke-linecap", "round");
          this.elements.bonesGroup.appendChild(line);
        }
      }

      // Draw joints
      const drawnJoints = new Set();
      for (const [from, to] of BONES) {
        for (const jointName of [from, to]) {
          if (jointName.startsWith("_") || drawnJoints.has(jointName)) continue;

          const pos = this.toSvgCoords(this.getJointPosition(joints, jointName));
          if (pos) {
            const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
            circle.setAttribute("cx", pos[0]);
            circle.setAttribute("cy", pos[1]);
            circle.setAttribute("r", "6");
            circle.setAttribute("fill", COLORS.jointFill);
            circle.setAttribute("stroke", COLORS.joint);
            circle.setAttribute("stroke-width", "2");
            this.elements.jointsGroup.appendChild(circle);
            drawnJoints.add(jointName);
          }
        }
      }
    }

    setupClickHandler() {
      this.elements.clickCapture.addEventListener("click", (e) => {
        if (this.isComplete) return;

        // Get click position relative to SVG
        const rect = this.elements.svg.getBoundingClientRect();
        const scaleX = SVG_WIDTH / rect.width;
        const scaleY = SVG_HEIGHT / rect.height;
        const svgX = (e.clientX - rect.left) * scaleX;
        const svgY = (e.clientY - rect.top) * scaleY;

        const [normX, normY] = this.toNormalizedCoords(svgX, svgY);
        this.handleClick(normX, normY, svgX, svgY);
      });
    }

    handleClick(normX, normY, svgX, svgY) {
      this.attempts++;
      this.clickedX = normX;
      this.clickedY = normY;

      // Check if click is in correct zone
      const correctZone = this.question.correct_zone;
      const distToCorrect = this.distance(normX, normY, correctZone.x, correctZone.y);

      if (distToCorrect <= correctZone.radius) {
        this.handleCorrectClick(svgX, svgY);
        return;
      }

      // Check distractor zones
      for (const distractor of this.question.distractor_zones) {
        const distToDistractor = this.distance(normX, normY, distractor.x, distractor.y);
        if (distToDistractor <= 0.1) { // Distractor click radius
          this.handleDistractorClick(distractor.hint, svgX, svgY);
          return;
        }
      }

      // Generic miss
      this.handleMissClick(svgX, svgY);
    }

    distance(x1, y1, x2, y2) {
      return Math.sqrt(Math.pow(x2 - x1, 2) + Math.pow(y2 - y1, 2));
    }

    handleCorrectClick(svgX, svgY) {
      this.isCorrect = true;
      this.isComplete = true;

      // Show green pulse at click point
      this.showPulse(svgX, svgY, "correct");

      // Show success message
      this.elements.feedbackMessage.innerHTML = `<span class="feedback-correct">Correct!</span>`;
      this.elements.feedbackMessage.classList.add("show-correct");

      // Enable submit button with answer data
      this.enableSubmit();

      // Reveal explanation after a short delay
      setTimeout(() => this.revealAnswer(), 600);
    }

    handleDistractorClick(hint, svgX, svgY) {
      // Shake animation
      this.shakeContainer();

      // Show red indicator
      this.showPulse(svgX, svgY, "wrong");

      // Show hint
      this.elements.hintCallout.innerHTML = hint;
      this.elements.hintCallout.style.display = "block";
      this.elements.hintCallout.classList.add("show-hint");

      if (this.attempts >= this.maxAttempts) {
        this.isComplete = true;
        this.elements.feedbackMessage.innerHTML = `<span class="feedback-wrong">Not quite. Here's the answer:</span>`;
        this.enableSubmit();
        setTimeout(() => this.revealAnswer(), 400);
      } else {
        this.elements.feedbackMessage.innerHTML = `<span class="feedback-retry">Try again (${this.maxAttempts - this.attempts} attempt${this.maxAttempts - this.attempts !== 1 ? 's' : ''} left)</span>`;
      }
    }

    handleMissClick(svgX, svgY) {
      // Shake animation
      this.shakeContainer();

      // Show miss indicator
      this.showPulse(svgX, svgY, "miss");

      // Show generic hint
      this.elements.hintCallout.innerHTML = "Not quite — look for where the body is moving incorrectly.";
      this.elements.hintCallout.style.display = "block";
      this.elements.hintCallout.classList.add("show-hint");

      if (this.attempts >= this.maxAttempts) {
        this.isComplete = true;
        this.elements.feedbackMessage.innerHTML = `<span class="feedback-wrong">Not quite. Here's the answer:</span>`;
        this.enableSubmit();
        setTimeout(() => this.revealAnswer(), 400);
      } else {
        this.elements.feedbackMessage.innerHTML = `<span class="feedback-retry">Try again (${this.maxAttempts - this.attempts} attempt${this.maxAttempts - this.attempts !== 1 ? 's' : ''} left)</span>`;
      }
    }

    showPulse(svgX, svgY, type) {
      // Clear previous feedback
      this.elements.feedbackLayer.innerHTML = "";

      const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circle.setAttribute("cx", svgX);
      circle.setAttribute("cy", svgY);
      circle.setAttribute("r", "15");
      circle.classList.add(`pulse-${type}`);
      this.elements.feedbackLayer.appendChild(circle);
    }

    shakeContainer() {
      this.elements.canvasContainer.classList.add("shake");
      setTimeout(() => {
        this.elements.canvasContainer.classList.remove("shake");
      }, 400);
    }

    revealAnswer() {
      const correctZone = this.question.correct_zone;
      const svgX = correctZone.x * SVG_WIDTH;
      const svgY = correctZone.y * SVG_HEIGHT;
      const svgRadius = correctZone.radius * SVG_WIDTH;

      // Draw correct zone circle
      const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circle.setAttribute("cx", svgX);
      circle.setAttribute("cy", svgY);
      circle.setAttribute("r", svgRadius);
      circle.classList.add("correct-zone-reveal");
      this.elements.feedbackLayer.appendChild(circle);

      // Add label
      const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
      text.setAttribute("x", svgX);
      text.setAttribute("y", svgY + svgRadius + 20);
      text.setAttribute("text-anchor", "middle");
      text.setAttribute("class", "correct-zone-label");
      text.textContent = correctZone.label;
      this.elements.feedbackLayer.appendChild(text);

      // Show explanation
      this.elements.explanationBox.innerHTML = `<strong>Explanation:</strong> ${this.question.explanation || ""}`;
      this.elements.explanationBox.style.display = "block";
      this.elements.explanationBox.classList.add("show-explanation");
    }

    enableSubmit() {
      const submitBtn = document.getElementById("submit-btn");
      if (submitBtn) {
        submitBtn.disabled = false;
        // Store the answer data on the button for the submit handler
        $(submitBtn).data("spot-click-answer", {
          question_id: this.question.id,
          clicked_x: this.clickedX,
          clicked_y: this.clickedY,
          correct: this.isCorrect,
          attempts: this.attempts,
        });
      }
    }
  }

  // Static init method
  CompensationClick.init = function (container, question) {
    return new CompensationClick(container, question);
  };

  // Export
  window.CompensationClick = CompensationClick;
})(window);

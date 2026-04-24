/**
 * Skeleton Player - Vanilla JS component for animating pose skeleton data
 *
 * Usage:
 *   <div class="skeleton-player" data-src="/static/skeletons/good_squat.json" data-variant="good"></div>
 *   <script src="/static/js/skeleton_player.js"></script>
 *   <script>SkeletonPlayer.initAll();</script>
 */

(function (window) {
  "use strict";

  // SVG dimensions (viewBox)
  const SVG_WIDTH = 400;
  const SVG_HEIGHT = 500;

  // Colors
  const COLORS = {
    good: {
      bone: "#2E5E4E",
      joint: "#2E5E4E",
      jointFill: "#D4E8DD",
    },
    bad: {
      bone: "#C94A4A",
      joint: "#C94A4A",
      jointFill: "#F5D6D6",
    },
  };

  // Bone connections: [from, to]
  const BONES = [
    // Torso
    ["left_shoulder", "right_shoulder"], // Chest
    ["left_hip", "right_hip"], // Pelvis
    ["left_shoulder", "left_hip"], // Left torso side
    ["right_shoulder", "right_hip"], // Right torso side

    // Neck (shoulder midpoint to nose)
    ["_neck_midpoint", "nose"],

    // Arms
    ["left_shoulder", "left_elbow"],
    ["left_elbow", "left_wrist"],
    ["right_shoulder", "right_elbow"],
    ["right_elbow", "right_wrist"],

    // Legs
    ["left_hip", "left_knee"],
    ["left_knee", "left_ankle"],
    ["left_ankle", "left_heel"],
    ["right_hip", "right_knee"],
    ["right_knee", "right_ankle"],
    ["right_ankle", "right_heel"],
  ];

  // Joints to display angles for (when toggle is on)
  const ANGLE_JOINTS = ["left_knee", "right_knee", "left_hip", "right_hip", "lower_back"];

  // Mapping joint names to their angle keys (for hover tooltip)
  const JOINT_ANGLE_MAP = {
    left_elbow: "left_elbow",
    right_elbow: "right_elbow",
    left_shoulder: "left_shoulder",
    right_shoulder: "right_shoulder",
    left_hip: "left_hip",
    right_hip: "right_hip",
    left_knee: "left_knee",
    right_knee: "right_knee",
    left_ankle: "left_ankle",
    right_ankle: "right_ankle",
    // no angle for nose, wrists, heels
  };

  /**
   * Convert joint name to display format: left_knee -> Left Knee
   */
  function formatJointName(jointName) {
    return jointName
      .split("_")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  }

  /**
   * SkeletonPlayer class
   */
  class SkeletonPlayer {
    constructor(container) {
      this.container = container;
      this.src = container.dataset.src;
      this.variant = container.dataset.variant || "good";
      this.colors = COLORS[this.variant] || COLORS.good;

      this.data = null;
      this.currentFrame = 0;
      this.isPlaying = false;
      this.showAngles = false;
      this.lastTimestamp = 0;
      this.frameDuration = 0;
      this.animationId = null;

      // Hover tooltip state
      this.hoveredJoint = null;
      this.jointCircles = new Map(); // Map of joint name -> circle element

      this.elements = {};
      this.init();
    }

    async init() {
      this.render();
      await this.loadData();
      if (this.data) {
        this.frameDuration = 1000 / this.data.fps;
        this.drawFrame(0);
        this.play();
      }
    }

    render() {
      this.container.innerHTML = `
        <div class="skeleton-canvas-wrapper">
          <svg class="skeleton-svg" viewBox="0 0 ${SVG_WIDTH} ${SVG_HEIGHT}" preserveAspectRatio="xMidYMid meet">
            <g class="skeleton-bones"></g>
            <g class="skeleton-joints"></g>
            <g class="skeleton-angles"></g>
            <g class="skeleton-tooltip-layer"></g>
          </svg>
        </div>
        <div class="skeleton-controls">
          <button class="skeleton-play-btn" title="Play/Pause">
            <span class="play-icon">&#9658;</span>
            <span class="pause-icon" style="display:none;">&#10074;&#10074;</span>
          </button>
          <input type="range" class="skeleton-scrubber" min="0" max="100" value="0">
          <span class="skeleton-frame-counter">0 / 0</span>
          <label class="skeleton-angle-toggle">
            <input type="checkbox" class="skeleton-angle-checkbox">
            <span>Angles</span>
          </label>
        </div>
      `;

      // Cache elements
      this.elements.svg = this.container.querySelector(".skeleton-svg");
      this.elements.bonesGroup = this.container.querySelector(".skeleton-bones");
      this.elements.jointsGroup = this.container.querySelector(".skeleton-joints");
      this.elements.anglesGroup = this.container.querySelector(".skeleton-angles");
      this.elements.tooltipLayer = this.container.querySelector(".skeleton-tooltip-layer");
      this.elements.playBtn = this.container.querySelector(".skeleton-play-btn");
      this.elements.playIcon = this.container.querySelector(".play-icon");
      this.elements.pauseIcon = this.container.querySelector(".pause-icon");
      this.elements.scrubber = this.container.querySelector(".skeleton-scrubber");
      this.elements.frameCounter = this.container.querySelector(".skeleton-frame-counter");
      this.elements.angleCheckbox = this.container.querySelector(".skeleton-angle-checkbox");

      // Event listeners
      this.elements.playBtn.addEventListener("click", () => this.togglePlay());

      this.elements.scrubber.addEventListener("input", () => {
        this.pause();
        const frame = Math.floor(
          (this.elements.scrubber.value / 100) * (this.data.frames.length - 1)
        );
        this.currentFrame = frame;
        this.drawFrame(frame);
      });

      this.elements.scrubber.addEventListener("change", () => {
        this.play();
      });

      this.elements.angleCheckbox.addEventListener("change", (e) => {
        this.showAngles = e.target.checked;
        this.drawFrame(this.currentFrame);
      });
    }

    async loadData() {
      try {
        const response = await fetch(this.src);
        if (!response.ok) {
          throw new Error(`Failed to load: ${response.status}`);
        }
        this.data = await response.json();
        this.elements.scrubber.max = 100;
        this.updateFrameCounter();
      } catch (error) {
        console.error("SkeletonPlayer: Failed to load data", error);
        this.container.innerHTML = `<div class="skeleton-error">Failed to load skeleton data</div>`;
      }
    }

    getJointPosition(joints, name) {
      // Special case: neck midpoint
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

    drawFrame(frameIndex) {
      if (!this.data || frameIndex >= this.data.frames.length) return;

      const frame = this.data.frames[frameIndex];
      const joints = frame.joints;
      const angles = frame.angles || {};

      // Clear previous frame
      this.elements.bonesGroup.innerHTML = "";
      this.elements.jointsGroup.innerHTML = "";
      this.elements.anglesGroup.innerHTML = "";

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
          line.setAttribute("stroke", this.colors.bone);
          line.setAttribute("stroke-width", "3");
          line.setAttribute("stroke-linecap", "round");
          this.elements.bonesGroup.appendChild(line);
        }
      }

      // Draw joints
      const drawnJoints = new Set();
      this.jointCircles.clear();

      for (const [from, to] of BONES) {
        for (const jointName of [from, to]) {
          if (jointName.startsWith("_") || drawnJoints.has(jointName)) continue;

          const pos = this.toSvgCoords(this.getJointPosition(joints, jointName));
          if (pos) {
            const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
            circle.setAttribute("cx", pos[0]);
            circle.setAttribute("cy", pos[1]);
            circle.setAttribute("r", "6");
            circle.setAttribute("fill", this.colors.jointFill);
            circle.setAttribute("stroke", this.colors.joint);
            circle.setAttribute("stroke-width", "2");
            circle.setAttribute("data-joint", jointName);
            circle.setAttribute("tabindex", "0");
            circle.style.cursor = "pointer";

            // Apply hover state if this joint is currently hovered
            if (this.hoveredJoint === jointName) {
              circle.setAttribute("r", "9");
              circle.classList.add("joint-hovered");
              circle.setAttribute("stroke", this.colors.bone);
            }

            // Event handlers for hover tooltip
            circle.addEventListener("mouseenter", () => this.handleJointEnter(jointName));
            circle.addEventListener("mouseleave", () => this.handleJointLeave(jointName));
            circle.addEventListener("focus", () => this.handleJointEnter(jointName));
            circle.addEventListener("blur", () => this.handleJointLeave(jointName));

            this.elements.jointsGroup.appendChild(circle);
            this.jointCircles.set(jointName, circle);
            drawnJoints.add(jointName);
          }
        }
      }

      // Update tooltip if a joint is currently hovered
      if (this.hoveredJoint) {
        this.updateTooltip();
      }

      // Draw angle labels if enabled
      if (this.showAngles) {
        for (const jointName of ANGLE_JOINTS) {
          const angleKey = jointName;
          const angle = angles[angleKey];
          if (angle === undefined) continue;

          // Determine position for label
          let pos = null;
          if (jointName === "lower_back") {
            // Position between hips
            const lh = joints["left_hip"];
            const rh = joints["right_hip"];
            if (lh && rh) {
              pos = this.toSvgCoords([(lh[0] + rh[0]) / 2, (lh[1] + rh[1]) / 2 - 0.05]);
            }
          } else {
            pos = this.toSvgCoords(joints[jointName]);
          }

          if (pos) {
            const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
            text.setAttribute("x", pos[0] + 15);
            text.setAttribute("y", pos[1] - 5);
            text.setAttribute("fill", this.colors.bone);
            text.setAttribute("font-size", "12");
            text.setAttribute("font-family", "sans-serif");
            text.textContent = `${Math.round(angle)}°`;
            this.elements.anglesGroup.appendChild(text);
          }
        }
      }

      this.updateFrameCounter();
      this.updateScrubber();
    }

    updateFrameCounter() {
      if (!this.data) return;
      this.elements.frameCounter.textContent = `${this.currentFrame + 1} / ${this.data.frames.length}`;
    }

    updateScrubber() {
      if (!this.data) return;
      const percent = (this.currentFrame / (this.data.frames.length - 1)) * 100;
      this.elements.scrubber.value = percent;
    }

    play() {
      if (this.isPlaying) return;
      this.isPlaying = true;
      this.elements.playIcon.style.display = "none";
      this.elements.pauseIcon.style.display = "inline";
      this.lastTimestamp = performance.now();
      this.animate();
    }

    pause() {
      this.isPlaying = false;
      this.elements.playIcon.style.display = "inline";
      this.elements.pauseIcon.style.display = "none";
      if (this.animationId) {
        cancelAnimationFrame(this.animationId);
        this.animationId = null;
      }
    }

    togglePlay() {
      if (this.isPlaying) {
        this.pause();
      } else {
        this.play();
      }
    }

    animate(timestamp) {
      if (!this.isPlaying) return;

      if (!timestamp) timestamp = performance.now();

      const elapsed = timestamp - this.lastTimestamp;

      if (elapsed >= this.frameDuration) {
        this.currentFrame++;
        if (this.currentFrame >= this.data.frames.length) {
          this.currentFrame = 0; // Loop
        }
        this.drawFrame(this.currentFrame);
        this.lastTimestamp = timestamp;
      }

      this.animationId = requestAnimationFrame((t) => this.animate(t));
    }

    handleJointEnter(jointName) {
      this.hoveredJoint = jointName;

      // Highlight the joint circle
      const circle = this.jointCircles.get(jointName);
      if (circle) {
        circle.setAttribute("r", "9");
        circle.classList.add("joint-hovered");
        circle.setAttribute("stroke", this.colors.bone);
      }

      this.showTooltip(jointName);
    }

    handleJointLeave(jointName) {
      if (this.hoveredJoint !== jointName) return;

      this.hoveredJoint = null;

      // Reset the joint circle
      const circle = this.jointCircles.get(jointName);
      if (circle) {
        circle.setAttribute("r", "6");
        circle.classList.remove("joint-hovered");
        circle.setAttribute("stroke", this.colors.joint);
      }

      this.hideTooltip();
    }

    showTooltip(jointName) {
      this.updateTooltip();
    }

    hideTooltip() {
      this.elements.tooltipLayer.innerHTML = "";
    }

    updateTooltip() {
      if (!this.hoveredJoint || !this.data) return;

      const frame = this.data.frames[this.currentFrame];
      const joints = frame.joints;
      const angles = frame.angles || {};

      const jointName = this.hoveredJoint;
      const pos = this.toSvgCoords(this.getJointPosition(joints, jointName));
      if (!pos) return;

      // Get angle if this joint has one
      const angleKey = JOINT_ANGLE_MAP[jointName];
      const angle = angleKey ? angles[angleKey] : undefined;

      // Build tooltip text
      const displayName = formatJointName(jointName);
      const tooltipText = angle !== undefined
        ? `${displayName}  ${Math.round(angle)}°`
        : displayName;

      // Calculate tooltip dimensions
      const padding = 6;
      const fontSize = 11;
      const charWidth = fontSize * 0.6;
      const textWidth = tooltipText.length * charWidth;
      const boxWidth = textWidth + padding * 2;
      const boxHeight = fontSize + padding * 2;

      // Default position: 12px up and right
      const offsetX = 12;
      const offsetY = -12;
      let tooltipX = pos[0] + offsetX;
      let tooltipY = pos[1] + offsetY - boxHeight;

      // Check if tooltip goes outside viewBox and flip if needed
      const flipX = tooltipX + boxWidth > SVG_WIDTH;
      const flipY = tooltipY < 0;

      if (flipX) {
        tooltipX = pos[0] - offsetX - boxWidth;
      }
      if (flipY) {
        tooltipY = pos[1] + offsetY + 12;
      }

      // Clamp to viewBox bounds
      tooltipX = Math.max(2, Math.min(tooltipX, SVG_WIDTH - boxWidth - 2));
      tooltipY = Math.max(2, Math.min(tooltipY, SVG_HEIGHT - boxHeight - 2));

      // Clear and create tooltip
      this.elements.tooltipLayer.innerHTML = "";

      const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
      g.classList.add("joint-tooltip");

      const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      rect.setAttribute("x", tooltipX);
      rect.setAttribute("y", tooltipY);
      rect.setAttribute("width", boxWidth);
      rect.setAttribute("height", boxHeight);

      const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
      text.setAttribute("x", tooltipX + padding);
      text.setAttribute("y", tooltipY + fontSize + padding - 2);
      text.textContent = tooltipText;

      g.appendChild(rect);
      g.appendChild(text);
      this.elements.tooltipLayer.appendChild(g);
    }

    destroy() {
      this.pause();
      this.hoveredJoint = null;
      this.jointCircles.clear();
      this.container.innerHTML = "";
    }

    /**
     * Change the skeleton data source and reload
     * @param {string} url - New JSON source URL
     * @param {string} [variant] - Optional variant (good/bad)
     */
    async setSource(url, variant) {
      this.pause();
      this.src = url;
      if (variant) {
        this.variant = variant;
        this.colors = COLORS[this.variant] || COLORS.good;
      }
      this.data = null;
      this.currentFrame = 0;
      this.hoveredJoint = null;

      // Clear current display
      this.elements.bonesGroup.innerHTML = "";
      this.elements.jointsGroup.innerHTML = "";
      this.elements.anglesGroup.innerHTML = "";
      this.elements.tooltipLayer.innerHTML = "";
      this.jointCircles.clear();

      await this.loadData();
      if (this.data) {
        this.frameDuration = 1000 / this.data.fps;
        this.drawFrame(0);
        this.play();
      }
    }
  }

  /**
   * Initialize all skeleton players on the page
   */
  SkeletonPlayer.initAll = function () {
    const containers = document.querySelectorAll(".skeleton-player");
    const players = [];
    containers.forEach((container) => {
      players.push(new SkeletonPlayer(container));
    });
    return players;
  };

  // Export
  window.SkeletonPlayer = SkeletonPlayer;
})(window);

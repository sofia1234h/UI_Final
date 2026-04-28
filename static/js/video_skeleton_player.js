/**
 * Video Skeleton Player - Syncs video playback with CSV skeleton overlay
 *
 * Usage:
 *   <div class="video-skeleton-player"
 *        data-video="/static/videos/good_squat.mov"
 *        data-csv="/static/csvs/good_squat.csv"
 *        data-variant="good"></div>
 *   <script src="/static/js/video_skeleton_player.js"></script>
 *   <script>VideoSkeletonPlayer.initAll();</script>
 */

(function(window) {
  "use strict";

  const COLORS = {
    good: {
      bone: "#2E5E4E",
      joint: "#2E5E4E",
      jointFill: "#D4E8DD"
    },
    bad: {
      bone: "#C94A4A",
      joint: "#C94A4A",
      jointFill: "#F5D6D6"
    }
  };

  // Bone connections for skeleton
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
    ["right_ankle", "right_heel"]
  ];

  // Joint names to display
  const JOINT_NAMES = [
    "nose", "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip", "left_knee",
    "right_knee", "left_ankle", "right_ankle", "left_heel", "right_heel"
  ];

  // Joints that have angles
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
    right_ankle: "right_ankle"
  };

  function formatJointName(jointName) {
    return jointName
      .split("_")
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  }

  class VideoSkeletonPlayer {
    constructor(container) {
      this.container = container;
      this.videoSrc = container.dataset.video;
      this.csvSrc = container.dataset.csv;
      this.variant = container.dataset.variant || "good";
      this.colors = COLORS[this.variant] || COLORS.good;
      this.skeletonRotation = parseInt(container.dataset.skeletonRotation) || 0;

      this.frames = [];
      this.currentFrameIndex = 0;
      this.animationId = null;
      this.wasPlayingBeforeHover = false;
      this.hoveredJoint = null;

      // Computed bounds for skeleton viewBox
      this.bounds = null;

      this.init();
    }

    async init() {
      this.render();
      await this.loadCSV();
      this.setupEventListeners();
      this.startAnimationLoop();
    }

    render() {
      this.container.innerHTML = `
        <div class="video-skeleton-wrapper">
          <div class="vsp-layout">
            <div class="vsp-video-col">
              <video class="skeleton-video" playsinline muted loop>
                <source src="${this.videoSrc}" type="video/mp4">
                <source src="${this.videoSrc}" type="video/quicktime">
              </video>
            </div>
            <div class="vsp-skeleton-col">
              <svg class="skeleton-svg" preserveAspectRatio="xMidYMid meet">
                <g class="skeleton-bones"></g>
                <g class="skeleton-joints"></g>
                <g class="skeleton-tooltip-layer"></g>
              </svg>
            </div>
          </div>
          <div class="video-skeleton-controls">
            <button class="video-play-btn" title="Play/Pause">
              <span class="play-icon">&#9658;</span>
              <span class="pause-icon" style="display:none;">&#10074;&#10074;</span>
            </button>
            <input type="range" class="video-scrubber" min="0" max="100" value="0" step="0.1">
            <span class="video-time">0:00 / 0:00</span>
          </div>
        </div>
      `;

      // Cache elements
      this.video = this.container.querySelector(".skeleton-video");
      this.svg = this.container.querySelector(".skeleton-svg");
      this.bonesGroup = this.container.querySelector(".skeleton-bones");
      this.jointsGroup = this.container.querySelector(".skeleton-joints");
      this.tooltipLayer = this.container.querySelector(".skeleton-tooltip-layer");
      this.playBtn = this.container.querySelector(".video-play-btn");
      this.playIcon = this.container.querySelector(".play-icon");
      this.pauseIcon = this.container.querySelector(".pause-icon");
      this.scrubber = this.container.querySelector(".video-scrubber");
      this.timeDisplay = this.container.querySelector(".video-time");
    }

    async loadCSV() {
      try {
        const response = await fetch(this.csvSrc);
        const text = await response.text();
        this.parseCSV(text);
      } catch (error) {
        console.error("VideoSkeletonPlayer: Failed to load CSV", error);
      }
    }

    parseCSV(text) {
      const lines = text.trim().split("\n");
      const headers = lines[0].split(",");

      // Create index map for faster lookup
      const headerIndex = {};
      headers.forEach((h, i) => headerIndex[h] = i);

      for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(",");
        const frame = {
          frameNumber: parseInt(values[headerIndex["frame_number"]]),
          timestampMs: parseFloat(values[headerIndex["timestamp_ms"]]),
          joints: {},
          angles: {}
        };

        // Parse landmarks
        for (const jointName of JOINT_NAMES) {
          const xKey = `landmark_${jointName}_x`;
          const yKey = `landmark_${jointName}_y`;
          const visKey = `landmark_${jointName}_visibility`;

          if (headerIndex[xKey] !== undefined && headerIndex[yKey] !== undefined) {
            const x = parseFloat(values[headerIndex[xKey]]);
            const y = parseFloat(values[headerIndex[yKey]]);
            const vis = parseFloat(values[headerIndex[visKey]] || 1);

            if (!isNaN(x) && !isNaN(y) && vis > 0.3) {
              frame.joints[jointName] = [x, y];
            }
          }
        }

        // Parse angles
        for (const angleName of Object.keys(JOINT_ANGLE_MAP)) {
          const angleKey = `angle_${angleName}`;
          if (headerIndex[angleKey] !== undefined) {
            const angle = parseFloat(values[headerIndex[angleKey]]);
            if (!isNaN(angle)) {
              frame.angles[angleName] = angle;
            }
          }
        }

        this.frames.push(frame);
      }

      // Apply skeleton rotation if specified (before computing bounds)
      if (this.skeletonRotation) {
        this.rotateCoordinates(this.skeletonRotation);
      }

      // Compute bounds from all frames
      this.computeBounds();
    }

    rotateCoordinates(rotation) {
      // First compute bounds on raw (unrotated) coords
      let minX = Infinity, minY = Infinity;
      let maxX = -Infinity, maxY = -Infinity;

      for (const frame of this.frames) {
        for (const coords of Object.values(frame.joints)) {
          minX = Math.min(minX, coords[0]);
          minY = Math.min(minY, coords[1]);
          maxX = Math.max(maxX, coords[0]);
          maxY = Math.max(maxY, coords[1]);
        }
      }

      // Rotate each joint coordinate
      for (const frame of this.frames) {
        const newJoints = {};
        for (const [name, [x, y]] of Object.entries(frame.joints)) {
          let nx, ny;
          if (rotation === 90) {
            // 90° clockwise
            nx = maxY - y;
            ny = x - minX;
          } else if (rotation === 180) {
            nx = maxX - x;
            ny = maxY - y;
          } else if (rotation === 270) {
            // 90° counter-clockwise (270° clockwise)
            nx = y - minY;
            ny = maxX - x;
          } else {
            nx = x - minX;
            ny = y - minY;
          }
          newJoints[name] = [nx, ny];
        }
        frame.joints = newJoints;
      }
    }

    computeBounds() {
      let minX = Infinity, minY = Infinity;
      let maxX = -Infinity, maxY = -Infinity;

      for (const frame of this.frames) {
        for (const jointName of Object.keys(frame.joints)) {
          const [x, y] = frame.joints[jointName];
          minX = Math.min(minX, x);
          minY = Math.min(minY, y);
          maxX = Math.max(maxX, x);
          maxY = Math.max(maxY, y);
        }
      }

      // Add 5% padding
      const width = maxX - minX;
      const height = maxY - minY;
      const padX = width * 0.05;
      const padY = height * 0.05;

      this.bounds = {
        minX: minX - padX,
        minY: minY - padY,
        width: width + padX * 2,
        height: height + padY * 2
      };

      // Set the viewBox once
      this.svg.setAttribute("viewBox",
        `${this.bounds.minX} ${this.bounds.minY} ${this.bounds.width} ${this.bounds.height}`);
    }

    setupEventListeners() {
      // Play/Pause button
      this.playBtn.addEventListener("click", () => this.togglePlay());

      // Video events
      this.video.addEventListener("loadedmetadata", () => {
        this.updateTimeDisplay();
      });

      this.video.addEventListener("play", () => {
        this.playIcon.style.display = "none";
        this.pauseIcon.style.display = "inline";
      });

      this.video.addEventListener("pause", () => {
        this.playIcon.style.display = "inline";
        this.pauseIcon.style.display = "none";
      });

      // Scrubber
      this.scrubber.addEventListener("input", () => {
        const time = (this.scrubber.value / 100) * this.video.duration;
        this.video.currentTime = time;
      });

      // Auto-play when ready
      this.video.addEventListener("canplay", () => {
        this.video.play().catch(() => {});
      }, { once: true });
    }

    togglePlay() {
      if (this.video.paused) {
        this.video.play();
      } else {
        this.video.pause();
      }
    }

    startAnimationLoop() {
      const animate = () => {
        this.syncSkeletonToVideo();
        this.updateScrubber();
        this.updateTimeDisplay();
        this.animationId = requestAnimationFrame(animate);
      };
      animate();
    }

    syncSkeletonToVideo() {
      if (this.frames.length === 0) return;

      const currentTimeMs = this.video.currentTime * 1000;

      // Find the closest frame
      let closestIndex = 0;
      let minDiff = Infinity;

      for (let i = 0; i < this.frames.length; i++) {
        const diff = Math.abs(this.frames[i].timestampMs - currentTimeMs);
        if (diff < minDiff) {
          minDiff = diff;
          closestIndex = i;
        }
      }

      if (closestIndex !== this.currentFrameIndex) {
        this.currentFrameIndex = closestIndex;
        this.drawFrame(this.frames[closestIndex]);
      }
    }

    drawFrame(frame) {
      // viewBox is set once in computeBounds() - no need to update per frame

      // Clear previous
      this.bonesGroup.innerHTML = "";
      this.jointsGroup.innerHTML = "";

      const joints = frame.joints;

      // Draw bones
      for (const [from, to] of BONES) {
        const fromPos = this.getJointPosition(joints, from);
        const toPos = this.getJointPosition(joints, to);

        if (fromPos && toPos) {
          const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
          line.setAttribute("x1", fromPos[0]);
          line.setAttribute("y1", fromPos[1]);
          line.setAttribute("x2", toPos[0]);
          line.setAttribute("y2", toPos[1]);
          line.setAttribute("stroke", this.colors.bone);
          line.setAttribute("stroke-width", "4");
          line.setAttribute("stroke-linecap", "round");
          line.setAttribute("stroke-opacity", "0.9");
          this.bonesGroup.appendChild(line);
        }
      }

      // Draw joints
      const drawnJoints = new Set();

      for (const jointName of JOINT_NAMES) {
        if (drawnJoints.has(jointName)) continue;

        const pos = joints[jointName];
        if (!pos) continue;

        const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        circle.setAttribute("cx", pos[0]);
        circle.setAttribute("cy", pos[1]);
        circle.setAttribute("r", this.hoveredJoint === jointName ? "12" : "8");
        circle.setAttribute("fill", this.colors.jointFill);
        circle.setAttribute("stroke", this.colors.joint);
        circle.setAttribute("stroke-width", "3");
        circle.setAttribute("data-joint", jointName);
        circle.style.cursor = "pointer";

        // Hover events for auto-pause
        circle.addEventListener("mouseenter", () => this.handleJointEnter(jointName, frame));
        circle.addEventListener("mouseleave", () => this.handleJointLeave(jointName));

        this.jointsGroup.appendChild(circle);
        drawnJoints.add(jointName);
      }

      // Update tooltip if hovering
      if (this.hoveredJoint) {
        this.updateTooltip(frame);
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

    handleJointEnter(jointName, frame) {
      // Track if video was playing before hover
      this.wasPlayingBeforeHover = !this.video.paused;
      this.video.pause();

      this.hoveredJoint = jointName;
      this.showTooltip(jointName, frame);
    }

    handleJointLeave(jointName) {
      if (this.hoveredJoint !== jointName) return;

      // Resume if was playing before
      if (this.wasPlayingBeforeHover) {
        this.video.play();
      }

      this.hoveredJoint = null;
      this.hideTooltip();
    }

    showTooltip(jointName, frame) {
      this.updateTooltip(frame);
    }

    hideTooltip() {
      this.tooltipLayer.innerHTML = "";
    }

    updateTooltip(frame) {
      if (!this.hoveredJoint) return;

      const jointName = this.hoveredJoint;
      const pos = frame.joints[jointName];
      if (!pos) return;

      const angleKey = JOINT_ANGLE_MAP[jointName];
      const angle = angleKey ? frame.angles[angleKey] : undefined;

      const displayName = formatJointName(jointName);
      const tooltipText = angle !== undefined
        ? `${displayName}: ${Math.round(angle)}°`
        : displayName;

      // Calculate dimensions
      const padding = 8;
      const fontSize = 14;
      const charWidth = fontSize * 0.6;
      const boxWidth = tooltipText.length * charWidth + padding * 2;
      const boxHeight = fontSize + padding * 2;

      // Position tooltip
      let tooltipX = pos[0] + 15;
      let tooltipY = pos[1] - 15 - boxHeight;

      // Use computed bounds for positioning
      const bounds = this.bounds || { minX: 0, minY: 0, width: 640, height: 480 };
      const svgMinX = bounds.minX;
      const svgMinY = bounds.minY;
      const svgMaxX = bounds.minX + bounds.width;
      const svgMaxY = bounds.minY + bounds.height;

      // Flip if out of bounds
      if (tooltipX + boxWidth > svgMaxX) {
        tooltipX = pos[0] - 15 - boxWidth;
      }
      if (tooltipY < svgMinY) {
        tooltipY = pos[1] + 20;
      }

      // Clamp
      tooltipX = Math.max(svgMinX + 5, Math.min(tooltipX, svgMaxX - boxWidth - 5));
      tooltipY = Math.max(svgMinY + 5, Math.min(tooltipY, svgMaxY - boxHeight - 5));

      // Clear and create tooltip
      this.tooltipLayer.innerHTML = "";

      const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
      g.classList.add("video-tooltip");

      const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      rect.setAttribute("x", tooltipX);
      rect.setAttribute("y", tooltipY);
      rect.setAttribute("width", boxWidth);
      rect.setAttribute("height", boxHeight);
      rect.setAttribute("rx", "4");
      rect.setAttribute("fill", "rgba(0,0,0,0.85)");

      const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
      text.setAttribute("x", tooltipX + padding);
      text.setAttribute("y", tooltipY + fontSize + padding / 2);
      text.setAttribute("fill", "white");
      text.setAttribute("font-size", fontSize);
      text.setAttribute("font-family", "system-ui, sans-serif");
      text.textContent = tooltipText;

      g.appendChild(rect);
      g.appendChild(text);
      this.tooltipLayer.appendChild(g);
    }

    updateScrubber() {
      if (!this.video.duration) return;
      const percent = (this.video.currentTime / this.video.duration) * 100;
      this.scrubber.value = percent;
    }

    updateTimeDisplay() {
      const format = (t) => {
        const mins = Math.floor(t / 60);
        const secs = Math.floor(t % 60);
        return `${mins}:${secs.toString().padStart(2, "0")}`;
      };

      const current = format(this.video.currentTime || 0);
      const duration = format(this.video.duration || 0);
      this.timeDisplay.textContent = `${current} / ${duration}`;
    }

    destroy() {
      if (this.animationId) {
        cancelAnimationFrame(this.animationId);
      }
      this.video.pause();
      this.container.innerHTML = "";
    }
  }

  /**
   * Initialize all video skeleton players on the page
   */
  VideoSkeletonPlayer.initAll = function() {
    const containers = document.querySelectorAll(".video-skeleton-player");
    const players = [];
    containers.forEach(container => {
      players.push(new VideoSkeletonPlayer(container));
    });
    return players;
  };

  // Export
  window.VideoSkeletonPlayer = VideoSkeletonPlayer;
})(window);

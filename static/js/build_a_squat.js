/**
 * Build-a-Squat Interactive Component
 * Demonstrates causal relationships between mobility/control limitations and squat compensations
 */

(function (window) {
  "use strict";

  const BuildASquat = {
    /**
     * Initialize the Build-a-Squat interactive
     * @param {HTMLElement} container - The container element
     * @param {Object} lessonData - The lesson configuration from JSON
     */
    init(container, lessonData) {
      this.container = container;
      this.lessonData = lessonData;
      this.inputs = {};
      this.skeletonPlayer = null;

      // Set default input values (all "good")
      for (const input of lessonData.inputs) {
        this.inputs[input.id] = input.options[0].value;
      }

      this.render();
      this.initSkeletonPlayer();
      this.updateOutcome();
    },

    /**
     * Render the component HTML
     */
    render() {
      const inputsHtml = this.lessonData.inputs
        .map((input) => this.renderInputGroup(input))
        .join("");

      this.container.innerHTML = `
        <div class="bas-layout">
          <div class="bas-inputs">
            ${inputsHtml}
          </div>
          <div class="bas-skeleton-panel">
            <div class="bas-skeleton-container">
              <div id="bas-skeleton-player" class="skeleton-player"></div>
              <div class="bas-skeleton-placeholder" style="display: none;">
                <p>Skeleton data loading — regenerate from CSVs</p>
              </div>
            </div>
            <div class="bas-outcome">
              <div class="bas-outcome-header">
                <span class="bas-outcome-label"></span>
                <span class="bas-score-badge"></span>
              </div>
              <div class="bas-explanation"></div>
            </div>
          </div>
        </div>
      `;

      // Cache elements
      this.elements = {
        skeletonPlayer: this.container.querySelector("#bas-skeleton-player"),
        placeholder: this.container.querySelector(".bas-skeleton-placeholder"),
        outcomeLabel: this.container.querySelector(".bas-outcome-label"),
        scoreBadge: this.container.querySelector(".bas-score-badge"),
        explanation: this.container.querySelector(".bas-explanation"),
      };

      // Attach event listeners to all radio buttons
      this.container.querySelectorAll('input[type="radio"]').forEach((radio) => {
        radio.addEventListener("change", (e) => this.handleInputChange(e));
      });
    },

    /**
     * Render a single input group with radio button toggles
     */
    renderInputGroup(input) {
      const optionsHtml = input.options
        .map(
          (opt, idx) => `
          <input type="radio"
                 class="btn-check"
                 name="${input.id}"
                 id="${input.id}_${opt.value}"
                 value="${opt.value}"
                 ${idx === 0 ? "checked" : ""}>
          <label class="btn btn-outline-success" for="${input.id}_${opt.value}">
            ${opt.label}
          </label>
        `
        )
        .join("");

      return `
        <div class="bas-input-group">
          <label class="bas-input-label">${input.label}</label>
          <div class="btn-group" role="group" aria-label="${input.label}">
            ${optionsHtml}
          </div>
        </div>
      `;
    },

    /**
     * Initialize the skeleton player
     */
    initSkeletonPlayer() {
      const outcome = this.findMatchingOutcome();
      const skeletonUrl = `/static/skeletons/${outcome.skeleton}`;

      // Set initial source on the container
      this.elements.skeletonPlayer.dataset.src = skeletonUrl;
      this.elements.skeletonPlayer.dataset.variant =
        outcome.score === 3 ? "good" : "bad";

      // Create player instance
      this.skeletonPlayer = new SkeletonPlayer(this.elements.skeletonPlayer);
    },

    /**
     * Handle input radio button changes
     */
    handleInputChange(e) {
      const inputId = e.target.name;
      const value = e.target.value;
      this.inputs[inputId] = value;
      this.updateOutcome();
    },

    /**
     * Find the first matching outcome based on current inputs
     */
    findMatchingOutcome() {
      for (const outcome of this.lessonData.outcomes) {
        const whenKeys = Object.keys(outcome.when);
        const matches = whenKeys.every(
          (key) => this.inputs[key] === outcome.when[key]
        );
        if (matches) {
          return outcome;
        }
      }
      // Fallback to first outcome if no match (shouldn't happen)
      return this.lessonData.outcomes[0];
    },

    /**
     * Update the display based on current inputs
     */
    async updateOutcome() {
      const outcome = this.findMatchingOutcome();
      const skeletonUrl = `/static/skeletons/${outcome.skeleton}`;
      const variant = outcome.score === 3 ? "good" : "bad";

      // Update skeleton player source
      if (this.skeletonPlayer) {
        try {
          await this.skeletonPlayer.setSource(skeletonUrl, variant);
          this.elements.skeletonPlayer.style.display = "";
          this.elements.placeholder.style.display = "none";
        } catch (error) {
          // Show placeholder if skeleton fails to load
          this.elements.skeletonPlayer.style.display = "none";
          this.elements.placeholder.style.display = "flex";
        }
      }

      // Fade out explanation
      this.elements.explanation.classList.add("bas-fade-out");

      // Update after brief delay for fade effect
      setTimeout(() => {
        // Update outcome label
        this.elements.outcomeLabel.textContent = outcome.label;

        // Update score badge
        this.elements.scoreBadge.textContent = outcome.score;
        this.elements.scoreBadge.className = "bas-score-badge";
        if (outcome.score === 3) {
          this.elements.scoreBadge.classList.add("bas-score-green");
        } else if (outcome.score === 2) {
          this.elements.scoreBadge.classList.add("bas-score-amber");
        } else {
          this.elements.scoreBadge.classList.add("bas-score-red");
        }

        // Update explanation
        this.elements.explanation.textContent = outcome.explanation;

        // Update explanation border color
        this.elements.explanation.className = "bas-explanation";
        if (outcome.score === 3) {
          this.elements.explanation.classList.add("bas-explanation-green");
        } else if (outcome.score === 2) {
          this.elements.explanation.classList.add("bas-explanation-amber");
        } else {
          this.elements.explanation.classList.add("bas-explanation-red");
        }

        // Fade in
        this.elements.explanation.classList.remove("bas-fade-out");
      }, 100);

      // Log interaction to backend
      this.logInteraction(outcome);
    },

    /**
     * Log interaction to backend for telemetry
     */
    logInteraction(outcome) {
      fetch("/log-interaction", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          lesson_id: this.lessonData.id,
          inputs: { ...this.inputs },
          outcome_label: outcome.label,
        }),
      }).catch((err) => {
        // Silently fail - telemetry shouldn't break the UI
        console.warn("Failed to log interaction:", err);
      });
    },
  };

  // Export
  window.BuildASquat = BuildASquat;
})(window);

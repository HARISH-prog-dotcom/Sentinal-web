// Detection page: engine status and the model's training metrics (the tables are static HTML).

import { $ } from "../core/dom.js";
import { formatNumber, formatPercent } from "../core/format.js";

function setText(selector, value, format) {
  $(selector).textContent = value == null ? "–" : format ? format(value) : value;
}

export function renderDetection(model) {
  if (!model) return;
  const isLoaded = model.ml_loaded, badge = $("#engBadge");
  badge.textContent = isLoaded ? "Rules + ML model" : "Rules only (model not loaded)";
  badge.style.setProperty("--c", isLoaded ? "var(--safe)" : "var(--medium)");
  $("#engine").textContent = isLoaded && model.recall != null ? `Rules + ML · recall ${formatPercent(model.recall)}` : isLoaded ? "Rules + ML" : "Rules only";
  setText("#mAcc", model.accuracy, formatPercent);
  setText("#mPrec", model.precision, formatPercent);
  setText("#mRec", model.recall, formatPercent);
  setText("#mFpr", model.false_positive_rate, (value) => (value * 100).toFixed(2) + "%");
  setText("#fData", model.dataset);
  setText("#fRows", model.rows_clean, formatNumber);
  setText("#fTrain", model.train_rows, formatNumber);
  setText("#fTest", model.test_rows, formatNumber);
  setText("#fThr", model.threshold, (value) => value.toFixed(2));
}

// Runs the one script that a built page carries, under Node, for tests/test_old_board.py. Node is the GitHub runner
// image's own, as it is for deploy.yml's deploy job, and this file needs no package.
//
// Standard input is JSON: the script's text, as the built page holds it, and a list of runs. Each run gives the
// clock, in milliseconds since 1970 in UTC, and the elements of the page that the script may look up: each by its
// id, with its attributes and its text, and the root element's attributes. A run may also give:
//
// - `dark`: whether the browser's own setting is dark, which window.matchMedia answers (false when not given);
// - `stored`: the theme kept in this browser's localStorage, or null (null when not given);
// - `late`: true to have the page's elements parsed after the script has run, as the page's one script, in the
//   head, meets them. Until then no element is found. Once the script has run, they are found, and each
//   MutationObserver it made is told, as the parser would tell it;
// - `ready`: true to fire DOMContentLoaded once the script has run, and `clicks`, a list of ids, to click each of
//   those elements in turn after it.
//
// Each run has a context of its own, which holds stand-ins for the document, window.matchMedia, localStorage, and
// MutationObserver, and a Date whose clock is the run's, and nothing else: no fetch, no timers, no require. Standard
// output is JSON: for each run, the elements' attributes and text once the script has run, the root element's
// attributes, what localStorage holds, the error it threw if it threw one, and every property of the document, of
// window, of localStorage, or of an element that it read or wrote, in order, so that a test can check it touched
// nothing else.

"use strict";

const vm = require("node:vm");

function stand_in(name, attributes, text, operations) {
  const state = { attributes: { ...attributes }, text };
  const listeners = {};
  const methods = {
    getAttribute(key) {
      operations.push(`${name}.getAttribute(${key})`);
      return Object.hasOwn(state.attributes, key) ? state.attributes[key] : null;
    },
    setAttribute(key, value) {
      operations.push(`${name}.setAttribute(${key})`);
      state.attributes[key] = String(value);
    },
    removeAttribute(key) {
      operations.push(`${name}.removeAttribute(${key})`);
      delete state.attributes[key];
    },
    addEventListener(type, listener) {
      operations.push(`${name}.addEventListener(${type})`);
      (listeners[type] ||= []).push(listener);
    },
  };
  const proxy = new Proxy(
    {},
    {
      get(_, key) {
        if (Object.hasOwn(methods, key)) return methods[key];
        operations.push(`${name}.${String(key)}`);
        return key === "textContent" ? state.text : undefined;
      },
      set(_, key, value) {
        operations.push(`${name}.${String(key)}=`);
        if (key === "textContent") state.text = String(value);
        return true;
      },
    },
  );
  return { proxy, state, listeners };
}

function run(script, { now, elements, root, dark = false, stored = null, late = false, ready = false, clicks = [] }) {
  const operations = [];
  const found = Object.fromEntries(
    Object.entries(elements).map(([id, element]) => [id, stand_in(id, element.attributes, element.text, operations)]),
  );
  const html = stand_in("root", root.attributes, "", operations);
  let parsed = !late;
  const documentListeners = {};
  const document = new Proxy(
    {},
    {
      get(_, key) {
        if (key === "getElementById") {
          return (id) => {
            operations.push(`document.getElementById(${id})`);
            return parsed && Object.hasOwn(found, id) ? found[id].proxy : null;
          };
        }
        if (key === "addEventListener") {
          return (type, listener) => {
            operations.push(`document.addEventListener(${type})`);
            (documentListeners[type] ||= []).push(listener);
          };
        }
        if (key === "querySelector" || key === "querySelectorAll") {
          return (selector) => {
            operations.push(`document.${key}(${selector})`);
            return key === "querySelector" ? null : [];
          };
        }
        operations.push(`document.${String(key)}`);
        return key === "documentElement" ? html.proxy : undefined;
      },
      set(_, key) {
        operations.push(`document.${String(key)}=`);
        return true;
      },
    },
  );
  // The browser's own colour scheme, as window.matchMedia answers for "(prefers-color-scheme: dark)".
  const window = new Proxy(
    {},
    {
      get(_, key) {
        operations.push(`window.${String(key)}`);
        if (key !== "matchMedia") return undefined;
        return (query) => {
          operations.push(`window.matchMedia(${query})`);
          return { matches: query === "(prefers-color-scheme: dark)" && dark, addEventListener() {} };
        };
      },
    },
  );
  const storage = { theme: stored };
  const localStorage = {
    getItem(key) {
      operations.push(`localStorage.getItem(${key})`);
      return Object.hasOwn(storage, key) ? storage[key] : null;
    },
    setItem(key, value) {
      operations.push(`localStorage.setItem(${key})`);
      storage[key] = String(value);
    },
    removeItem(key) {
      operations.push(`localStorage.removeItem(${key})`);
      storage[key] = null;
    },
  };
  // What the parser tells an observer of the document, in a run whose elements are parsed late.
  const observers = [];
  class MutationObserver {
    constructor(callback) {
      operations.push("new MutationObserver");
      this.callback = callback;
      this.watching = false;
      observers.push(this);
    }
    observe() {
      operations.push("MutationObserver.observe");
      this.watching = true;
    }
    disconnect() {
      operations.push("MutationObserver.disconnect");
      this.watching = false;
    }
  }
  // The clock passed in: Date.now() gives it, and so does a Date made with no argument.
  class Clock extends Date {
    constructor(...moment) {
      super(...(moment.length ? moment : [now]));
    }
    static now() {
      return now;
    }
  }
  let error = null;
  try {
    vm.runInContext(script, vm.createContext({ document, window, localStorage, MutationObserver, Date: Clock }), {
      timeout: 1000,
    });
    if (!parsed) {
      parsed = true;
      for (const observer of observers) if (observer.watching) observer.callback([], observer);
    }
    if (ready) {
      for (const listener of documentListeners.DOMContentLoaded || []) listener();
      for (const id of clicks) for (const listener of found[id].listeners.click || []) listener();
    }
  } catch (thrown) {
    error = String(thrown);
  }
  return {
    elements: Object.fromEntries(Object.entries(found).map(([id, { state }]) => [id, state])),
    root: html.state.attributes,
    stored: storage.theme,
    operations,
    error,
  };
}

const chunks = [];
process.stdin.on("data", (chunk) => chunks.push(chunk));
process.stdin.on("end", () => {
  const { script, runs } = JSON.parse(Buffer.concat(chunks).toString("utf8"));
  process.stdout.write(JSON.stringify(runs.map((each) => run(script, each))));
});

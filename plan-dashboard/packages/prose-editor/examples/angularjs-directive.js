/**
 * Using @asifhussain/prose-editor from AngularJS 1.x, with no bundler.
 *
 * Load the standalone build and the stylesheet from your server-side bundle
 * config (or two <script>/<link> tags), then register this directive:
 *
 *   dist/standalone/prose-editor.global.js   -> window.ProseEditor
 *   styles/prose-editor.css
 *
 * The point of the exercise: the toolbar, the extension points, the paste
 * sanitizer and the serializer guarantee are all available here, in a host with
 * no npm module resolution at runtime, using the same code the modern host runs.
 */
angular.module("app").directive("proseEditor", function () {
  return {
    restrict: "A",
    require: "ngModel",
    scope: { proseEditorOptions: "=?" },
    link: function (scope, element, attrs, ngModel) {
      var api = window.ProseEditor;

      var instance = api.mount(element[0], {
        // REQUIRED, always. There is no default serializer, deliberately:
        // a default is the same silent-data-loss trap the package exists to
        // close, moved up to the API.
        serializer: { kind: "markdown" },
        content: ngModel.$viewValue || "",
        toolbar: { ariaLabel: "Formatting" },
        bubble: {},

        // Your own UI, wired in. The package owns no modal implementation --
        // this host already has one, and two competing modal layers is worse
        // than none.
        ui: {
          openDialog: function (request) {
            // Route by `kind`; render whatever this app already renders.
            return scope.$root.myDialogService.open(request);
          },
        },

        // A custom insert, registered as ONE object -- icon, label, shortcut,
        // active-state and handler together, so a button and its accelerator
        // cannot drift apart.
        extensions: [],
      });

      // Angular <- editor
      instance.editor.on("update", function () {
        scope.$applyAsync(function () {
          ngModel.$setViewValue(instance.serialize());
        });
      });

      // Angular -> editor. Only on an EXTERNAL change: re-seeding on every
      // keystroke would fight the user and lose the caret.
      ngModel.$render = function () {
        if (ngModel.$viewValue !== instance.serialize()) {
          instance.editor.commands.setContent(ngModel.$viewValue || "");
        }
      };

      scope.$on("$destroy", function () {
        instance.destroy();
      });
    },
  };
});

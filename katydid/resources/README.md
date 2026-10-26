# About Resources

### default_tags.json
This file describes the list of default tags for the program. Default tag ids are manually generated and fixed. This way, there is no ambiguity for the id of default tags. The colors are also fixed by default at the moment.

### themes.json
Contains color codes for app themes. The themes contain the following parameters:
   * id - a unique string id for the theme
   * title - the title displayed to the user in the preferences menu
   * background - overall background window color
   * surface - background color of primary UI elements
   * text - UI text color
   * text-muted - Muted text color for timestamps and other secondary data
   * border - Border color for UI elements in the app
   * primary-fore - Primary accent color, this is the foreground if an element with two shades is applying the primary accent color
   * primary-back - Primary accent color, this is the background if an element with two shades is applying the primary accent color
   * secondary-back - Secondary accent color, this is the background if an element with two shades is applying the primary accent color
   * secondary-fore - Secondary accent color, this is the foreground if an element with two shades is applying the primary accent color
   * paper - When in the Entry text editor, this is the color of the writing surface
   * ink - When in the Entry text editor, this is the color of the text in the Entry body
   * selection - When an Entry or Collection is selected, it turns this color
   * error - Any error text displays in this color
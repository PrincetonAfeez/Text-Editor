# Schema Folder

This folder contains simple Mongoose schema files for a text editor application.

## Files

- `UserSchema.js` - stores user account information.
- `DocumentSchema.js` - stores text editor documents, owners, collaborators, tags, and visibility.
- `FolderSchema.js` - stores folders that organize documents.
- `index.js` - exports all schemas from one place.

## Usage

```js
const { User, Document, Folder } = require('./Schema');
```

These schemas assume the app uses Node.js, Express, MongoDB, and Mongoose.

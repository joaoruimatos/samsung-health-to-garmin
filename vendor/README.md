# Local dependency cache

This folder is reserved for a **local/private** dependency cache created with:

```powershell
.\setup.ps1 -CacheDependencies
```

Package archives and wheels in this folder are ignored by Git and must not be committed to the public repository.

In particular, do not mirror or redistribute Garmin's FIT SDK files here through GitHub. See `DEPENDENCIES.md` for the licensing reason and official download sources.

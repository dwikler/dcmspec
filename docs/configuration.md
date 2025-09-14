# Configuration and Caching

By default, downloaded specification documents (such as DICOM standards and IHE profiles) and generated data models (such as JSON files) are stored in a platform-specific cache directory. This location can be customized by specifying a configuration file.

## Default Cache Directory

- **Default cache directory location:**

    <div style="margin-bottom: 0.1em;">
      <span style="font-size:0.9em;">🍏 <strong>MacOS</strong></span><br>
      <span style="display:inline-block; margin-left:2em; font-size:0.9em;"><code>~/Library/Caches/dcmspec</code></span>
    </div>
    <div style="margin-bottom: 0.1em;">
      <span style="font-size:0.9em;">🐧 <strong>Linux</strong></span><br>
      <span style="display:inline-block; margin-left:2em; font-size:0.9em;"><code>~/.cache/dcmspec</code></span>
    </div>
    <div style="margin-bottom: 0.1em;">
      <span style="font-size:0.9em;">🪟 <strong>Windows</strong></span><br>
      <span style="display:inline-block; margin-left:2em; font-size:0.9em;"><code>%USERPROFILE%\AppData\Local\dcmspec\Cache</code></span>
    </div>

## Configuration of Cache Directory

The cache directory used by API and CLI applications can be changed by providing a configuration file.

This file can be named `config.json` and placed in the default configuration folder, or its location can be specified using the `--config` command-line option or the `DCMSPEC_CONFIG` environment variable.

- **Using the default config file**  
   If no config file is specified, dcmspec searches for `config.json` in the default configuration folder for the operating system:

    <div style="margin-bottom: 0.1em;">
      <span style="font-size:0.9em;">🍏 <strong>MacOS</strong></span><br>
      <span style="display:inline-block; margin-left:2em; font-size:0.9em;"><code>~/Library/Application Support/dcmspec</code></span>
    </div>
    <div style="margin-bottom: 0.1em;">
      <span style="font-size:0.9em;">🐧 <strong>Linux</strong></span><br>
      <span style="display:inline-block; margin-left:2em; font-size:0.9em;"><code>~/.config/dcmspec</code></span>
    </div>
    <div style="margin-bottom: 0.1em;">
      <span style="font-size:0.9em;">🪟 <strong>Windows</strong></span><br>
      <span style="display:inline-block; margin-left:2em; font-size:0.9em;"><code>%USERPROFILE%\AppData\Local\dcmspec</code></span><br>
      <span style="display:inline-block; margin-left:2em; font-size:0.9em;">or</span><br>
      <span style="display:inline-block; margin-left:2em; font-size:0.9em;"><code>%USERPROFILE%\AppData\Roaming\dcmspec</code></span>
    </div>

  Example `config.json`:

  ```json
  {
    "cache_dir": "./cache"
  }
  ```

- **Using the `--config` option:**  
   The path to the config file can be provided on the command line:

  ```bash
  poetry run python -m src.dcmspec.apps.cli.modattributes <table_id> --config myconfig.json
  ```

- **Using the `DCMSPEC_CONFIG` environment variable:**  
   The environment variable can be set to the path of the config file:

  ```bash
  export DCMSPEC_CONFIG=./myconfig.json
  poetry run python -m src.dcmspec.apps.cli.modattributes <table_id>
  ```

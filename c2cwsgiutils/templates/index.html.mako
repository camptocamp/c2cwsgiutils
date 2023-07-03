<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no" />
    <link
      rel="icon"
      type="image/png"
      sizes="32x32"
      href="${request.static_url('c2cwsgiutils:static/favicon-32x32.png')}"
      referrerpolicy="no-referrer"
    />
    <link
      rel="icon"
      type="image/png"
      sizes="16x16"
      href="${request.static_url('c2cwsgiutils:static/favicon-16x16.png')}"
      referrerpolicy="no-referrer"
    />
    <link
        rel="stylesheet"
        href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/css/bootstrap.min.css"
        integrity="sha512-GQGU0fMMi238uA+a/bdWJfpUGKUkBdgfFdgBm72SUQ6BeyWjoY/ton0tEjH+OSH9iP4Dfh+7HM0I9f5eR0L/4w=="
        crossorigin="anonymous"
        referrerpolicy="no-referrer"
    />
    <title>c2cwsgiutils tools</title>
    <style>
      body {
        margin-top: 0.5rem;
      }
      button, p  {
        margin-bottom: 0.5rem;
      }
    </style>
  </head>
  <body>
    <div class="container-fluid">
      ${ body | n }
    </div>
  </body>
</html>

FROM python:3.12-alpine

# Ensure that the environment uses UTF-8 encoding by default.
ENV LANG en_US.UTF-8

# Disable pip cache dir.
ENV PIP_NO_CACHE_DIR 1

# Allow pip install as root.
ENV PIP_ROOT_USER_ACTION ignore

# Stops Python default buffering to stdout, improving logging to the console.
ENV PYTHONUNBUFFERED 1

# Create a non-root user for the container.
ARG USERNAME=app
ARG USER_UID=1000
ARG USER_GID=$USER_UID
RUN addgroup \
    --gid $USER_GID \
    $USERNAME \
&& adduser \
    --uid $USER_UID \
    --ingroup $USERNAME \
    --disabled-password \
    $USERNAME

# Define app home and workdir.
ENV APP_HOME /home/$USERNAME
WORKDIR $APP_HOME

# Define frontend environment.
ENV YARN_VERSION "4.5.3"

# Copy the whole project except for what is in .dockerignore.
COPY --chown=$USERNAME:$USERNAME . .

# Update and install common OS packages.
RUN apk update --no-cache && apk upgrade --no-cache

# Build the backend.
RUN set -eux; \
        \
        # Needed at runtime.
        apk add --no-cache \
            libpq \
            libxslt \
            libxml2 \
        ; \
        # Needed only at build time, so we can delete after use.
        apk add --no-cache --virtual .backend-deps \
            gcc \
            libxml2-dev \
            libxslt-dev \
            linux-headers \
            musl-dev \
            pkgconf \
            python3-dev \
        ; \
        pip install -U pip; \
        pip install --no-cache-dir -r requirements/base.txt; \
        # Remove keys that aren't needed by the application but would be
        # flagged as a vulnerability by our Docker image scanner.
        rm /usr/local/lib/python3.12/site-packages/tornado/test/test.key; \
        rm /usr/local/lib/python3.12/site-packages/wpull/proxy/proxy.key; \
        rm /usr/local/lib/python3.12/site-packages/wpull/testing/test.pem; \
        apk del .backend-deps

# Build the frontend.
ENV NODE_ENV=production
RUN set -eux; \
        \
        # Needed only at build time, so we can delete after use.
        apk add --no-cache --virtual .frontend-deps npm \
        curl; \
        npm install -g corepack; \
        corepack enable; \
        corepack prepare yarn@${YARN_VERSION} --activate; \
        yarn install; \
        yarn build; \
        # We don't need node_modules once we've built our frontend.
        rm -rf ./node_modules; \
        apk del .frontend-deps

# Run the application with the user we created.
USER $USERNAME

ARG PORT=8000
EXPOSE $PORT
ENV PORT $PORT

CMD python manage.py runserver 0.0.0.0:$PORT

#!/usr/bin/env node
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
assert.equal(process.argv.length, 3, 'Pass the upstream Postiz checkout');
const src = fs.readFileSync(path.join(process.argv[2],
  'libraries/nestjs-libraries/src/integrations/social/youtube.provider.ts'), 'utf8');

function method(name) {
  const header = new RegExp('^  (?:override )?async ' + name + '\\(\\n', 'm');
  const start = src.search(header);
  assert(start >= 0, 'Missing provider method ' + name);
  const body = src.indexOf(' {', src.indexOf('): Promise<', start));
  const end = src.indexOf('\n  }\n', body);
  assert(body > start && end > body, 'Unrecognized provider method ' + name);
  const params = name === 'post'
    ? 'id, accessToken, postDetails, integration'
    : 'accessToken, pendingData, integration';
  return 'async ' + name + '(' + params + ')' + src.slice(body, end + 4)
    .replace('let probe: { videoId: string } | { uploadedBytes: number };', 'let probe;')
    .replace(/\bas any\b/g, '');
}
const abstract = fs.readFileSync(path.join(process.argv[2],
  'libraries/nestjs-libraries/src/integrations/social.abstract.ts'), 'utf8');
const wrapperStart = abstract.indexOf('  async runInConcurrent<T>(');
const wrapperBody = abstract.indexOf('\n  ) {', wrapperStart);
const wrapperEnd = abstract.indexOf('\n  }\n', wrapperBody);
assert(wrapperStart >= 0 && wrapperBody > wrapperStart && wrapperEnd > wrapperBody);
const wrapper = 'async runInConcurrent(func, ignoreConcurrency)' +
  abstract.slice(wrapperBody + 4, wrapperEnd + 4)
    .replace('let value: any;', 'let value;')
    .replace(/\{\} as any/g, '{}');
const methods = ['checkPostStatus', 'finalizePost', 'post'].map(method).join('\n') + '\n' + wrapper;
class BadBody extends Error {
  constructor(provider, body, payload, message) { super(message); this.provider = provider; }
}
class RefreshToken extends Error {}
class Disconnect extends Error {}
class PublishedWithError extends Error {
  constructor(provider, postDbId, releaseId, releaseURL, message) {
    super(message); Object.assign(this, { provider, postDbId, releaseId, releaseURL });
  }
}
function fixture(options = {}) {
  const h = {
    states: ['succeeded'], listCalls: 0, thumbnailCalls: 0, probeCalls: 0,
    uploadCalls: 0, streamCalls: 0, thumbnailReads: 0, delays: [], clock: 0,
    ...options,
  };
  const api = {
    videos: { list: async (request) => {
      h.listCalls++;
      assert.deepEqual(request.part, ['processingDetails']);
      assert.deepEqual(request.id, ['video-1']);
      if (h.listError) throw h.listError;
      const status = h.states[Math.min(h.listCalls - 1, h.states.length - 1)];
      return { data: { items: status === null ? [] :
        [{ id: 'video-1', processingDetails: status === undefined ? {} : { processingStatus: status } }] } };
    } },
    thumbnails: { set: async (request) => {
      h.thumbnailCalls++;
      assert.equal(request.videoId, 'video-1');
      if (h.thumbnailError) throw h.thumbnailError;
      return { data: { items: [{ default: { url: 'https://example.test/cover.jpg' } }] } };
    } },
  };
  const clientAndYoutube = () => ({
    client: { setCredentials: () => {} }, youtube: () => api,
  });
  const fakeFetch = async () => {
    h.uploadCalls++;
    return { status: 201, json: async () => ({ id: 'video-1' }) };
  };
  const RealDate = Date;
  class FakeDate extends RealDate { static now() { return h.clock; } }
  const Ctor = new Function('clientAndYoutube', 'BadBody', 'RefreshToken',
    'PublishedWithError', 'fetch', 'setHeartbeatDetails', 'Date', 'setTimeout', 'Disconnect', 'safeStringify',
    'return class YoutubeProvider { static YOUTUBE_UPLOAD_BATCH_MS = 60000; ' +
    'static YOUTUBE_CHUNK_SIZE = 8; identifier = "youtube";\n' + methods + '\n}')(clientAndYoutube,
    BadBody, RefreshToken, PublishedWithError, fakeFetch, () => {}, FakeDate,
    (cb, ms) => { h.delays.push(ms); h.clock += ms; cb(); }, Disconnect, JSON.stringify);
  const provider = new Ctor();
  provider.handleErrors = () => undefined;
  provider.probeUploadSession = async () => {
    h.probeCalls++;
    return h.probe || { videoId: 'video-1' };
  };
  provider.youtubeChunkStream = async () => { h.streamCalls++; return Buffer.from([1]); };
  provider.getSsrfSafeAxios = () => async () => {
    h.thumbnailReads++; return { data: 'image-stream' };
  };
  h.data = {
    uploadUri: 'https://example.test/upload/session', videoSize: 8,
    path: 'https://example.test/video.mp4', uploadedBytes: 0,
    thumbnail: 'https://example.test/cover.jpg', videoId: 'video-1', postDbId: 'post-1',
    ...(h.data || {}),
  };
  provider.postPending = async () => [{ id: 'post-1', status: 'pending', pendingData: h.data }];
  h.provider = provider;
  return h;
}

for (const state of ['processing', undefined, null]) {
  test('waits without setting thumbnail until processing is succeeded: ' + state, async () => {
    const h = fixture({ states: [state] });
    const out = await h.provider.finalizePost('token', h.data, {});
    assert.equal(out.status, 'pending');
    assert.equal(out.pendingData.videoId, 'video-1');
    assert.equal(out.pendingData.postDbId, 'post-1');
    assert.equal(h.listCalls, 1);
    assert.equal(h.thumbnailCalls, 0);
    assert.equal(h.thumbnailReads, 0);
    assert.equal(h.uploadCalls, 0);
  });
}
test('sets the thumbnail after succeeded and retains the published URL', async () => {
  const h = fixture();
  const out = await h.provider.finalizePost('token', h.data, {});
  assert.deepEqual(out, {
    status: 'completed', postId: 'video-1',
    releaseURL: 'https://www.youtube.com/watch?v=video-1',
  });
  assert.equal(h.listCalls, 1);
  assert.equal(h.thumbnailCalls, 1);
  assert.equal(h.probeCalls, 0);
});
for (const state of ['failed', 'terminated']) {
  test('reports terminal processing ' + state + ' with the existing video identifier', async () => {
    const h = fixture({ states: [state] });
    await assert.rejects(h.provider.finalizePost('token', h.data, {}),
      (err) => err instanceof PublishedWithError &&
        err.postDbId === 'post-1' && err.releaseId === 'video-1' &&
        err.releaseURL === 'https://www.youtube.com/watch?v=video-1');
    assert.equal(h.thumbnailCalls, 0);
    assert.equal(h.uploadCalls, 0);
  });
}
test('checkPostStatus does not probe an expired upload session when a videoId is known', async () => {
  const h = fixture();
  h.provider.probeUploadSession = async () => { throw new Error('Expired upload session must not be consulted'); };
  const out = await h.provider.checkPostStatus('token', h.data, {});
  assert.equal(out.status, 'ready');
  assert.equal(out.pendingData.videoId, 'video-1');
});
test('known video without thumbnail completes without upload probe or processing API request', async () => {
  const h = fixture({ data: { thumbnail: '' } });
  h.provider.probeUploadSession = async () => { throw new Error('No upload probe needed'); };
  const check = await h.provider.checkPostStatus('token', h.data, {});
  const final = await h.provider.finalizePost('token', h.data, {});
  assert.equal(check.status, 'completed');
  assert.equal(final.status, 'completed');
  assert.equal(check.postId, 'video-1');
  assert.equal(h.listCalls, 0);
  assert.equal(h.thumbnailCalls, 0);
});
test('a processing retry sets the cover once without uploading the video again', async () => {
  const h = fixture({ states: ['processing', 'succeeded'] });
  const pending = await h.provider.finalizePost('token', h.data, {});
  assert.equal(pending.status, 'pending');
  const ready = await h.provider.checkPostStatus('token', pending.pendingData, {});
  assert.equal(ready.status, 'ready');
  const final = await h.provider.finalizePost('token', ready.pendingData, {});
  assert.equal(final.status, 'completed');
  assert.equal(h.thumbnailCalls, 1);
  assert.equal(h.listCalls, 2);
  assert.equal(h.probeCalls, 0);
  assert.equal(h.uploadCalls, 0);
});
test('new upload preserves its identifier while processing and sends the video only once', async () => {
  const h = fixture({
    states: ['processing', 'succeeded'], probe: { uploadedBytes: 0 },
    data: { videoId: undefined },
  });
  const pending = await h.provider.finalizePost('token', h.data, {});
  assert.equal(pending.status, 'pending');
  assert.equal(pending.pendingData.videoId, 'video-1');
  assert.equal(h.uploadCalls, 1);
  const final = await h.provider.finalizePost('token', pending.pendingData, {});
  assert.equal(final.status, 'completed');
  assert.equal(h.probeCalls, 1);
  assert.equal(h.uploadCalls, 1);
  assert.equal(h.thumbnailCalls, 1);
});
test('transient processing API failure returns pending with the known videoId', async () => {
  const h = fixture({ listError: Object.assign(new Error('Connection reset'), { code: 'ECONNRESET' }) });
  const out = await h.provider.finalizePost('token', h.data, {});
  assert.equal(out.status, 'pending');
  assert.equal(out.pendingData.videoId, 'video-1');
  assert.equal(h.thumbnailCalls, 0);
  assert.equal(h.uploadCalls, 0);
});
test('token refresh errors still reach the native refresh and retry path', async () => {
  const error = new RefreshToken('token expired');
  const h = fixture({ listError: error });
  await assert.rejects(h.provider.finalizePost('token', h.data, {}), (err) => err === error);
  assert.equal(h.thumbnailCalls, 0);
});
test('a rejected thumbnail preserves the published identifier', async () => {
  const h = fixture({ thumbnailError: new BadBody('youtube', '{}', '{}', 'Thumbnail rejected') });
  await assert.rejects(h.provider.finalizePost('token', h.data, {}),
    (err) => err instanceof PublishedWithError && err.releaseId === 'video-1' &&
      err.postDbId === 'post-1');
  assert.equal(h.thumbnailCalls, 1);
  assert.equal(h.uploadCalls, 0);
});
test('an uncompleted upload session keeps its existing upload-resume path', async () => {
  const h = fixture({ probe: { uploadedBytes: 4 }, data: { videoId: undefined } });
  const out = await h.provider.checkPostStatus('token', h.data, {});
  assert.equal(out.status, 'ready');
  assert.equal(out.pendingData.uploadedBytes, 4);
  assert.equal(h.probeCalls, 1);
  assert.equal(h.listCalls, 0);
});
test('legacy post workflow waits between processing attempts instead of a tight loop', async () => {
  const h = fixture({ states: ['processing', 'succeeded'] });
  const out = await h.provider.post('account-1', 'token', [], {});
  assert.equal(out[0].status, 'success');
  assert.equal(out[0].postId, 'video-1');
  assert.deepEqual(h.delays, [10000]);
  assert.equal(h.listCalls, 2);
  assert.equal(h.thumbnailCalls, 1);
});
test('legacy processing timeout retains the video identifier and avoids new upload', async () => {
  const h = fixture({ states: ['processing'] });
  await assert.rejects(h.provider.post('account-1', 'token', [], {}),
    (err) => err instanceof PublishedWithError &&
      err.postDbId === 'post-1' && err.releaseId === 'video-1');
  assert(h.listCalls > 1 && h.listCalls <= 43);
  assert.equal(h.thumbnailCalls, 0);
  assert.equal(h.uploadCalls, 0);
});

for (const status of [429, 500, 503]) {
  test('processing status HTTP ' + status + ' retries while retaining the uploaded video', async () => {
    const error = Object.assign(new Error('Temporary API failure'), { response: { status } });
    const h = fixture({ listError: error });
    const out = await h.provider.finalizePost('token', h.data, {});
    assert.equal(out.status, 'pending');
    assert.equal(out.pendingData.videoId, 'video-1');
    assert.equal(h.thumbnailCalls, 0);
  });
}
test('permanent processing API rejection retains the native error classification', async () => {
  const error = Object.assign(new Error('Forbidden'), { response: { status: 403 } });
  const h = fixture({ listError: error });
  await assert.rejects(h.provider.finalizePost('token', h.data, {}),
    (err) => err instanceof PublishedWithError && err.releaseId === 'video-1');
  assert.equal(h.thumbnailCalls, 0);
});
test('an unknown programming error is not silently treated as a retryable network error', async () => {
  const h = fixture({ listError: new Error('Unexpected response handling bug') });
  await assert.rejects(h.provider.finalizePost('token', h.data, {}),
    (err) => err instanceof PublishedWithError && err.releaseId === 'video-1');
});

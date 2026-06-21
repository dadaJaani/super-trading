import { Controller, MessageEvent, Sse } from '@nestjs/common';
import { Observable } from 'rxjs';
import { StreamService } from './stream.service';

@Controller('stream')
export class StreamController {
  constructor(private readonly streamService: StreamService) {}

  @Sse('market')
  market(): Observable<MessageEvent> {
    return this.streamService.getMarketStream();
  }
}

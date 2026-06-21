import { Injectable, Logger, MessageEvent, OnModuleInit } from '@nestjs/common';
import { Observable, Subject } from 'rxjs';
import { RedisService } from '../redis/redis.service';

@Injectable()
export class StreamService implements OnModuleInit {
  private readonly logger = new Logger(StreamService.name);
  private readonly market$ = new Subject<MessageEvent>();

  constructor(private readonly redisService: RedisService) {}

  onModuleInit(): void {
    void this.redisService.subscribe('*', (channel, message) => {
      if (!channel.startsWith('price:') && !channel.startsWith('candles:')) {
        return;
      }

      let payload: unknown = message;
      try {
        payload = JSON.parse(message) as unknown;
      } catch {
        // keep raw string
      }

      const type = channel.startsWith('price:') ? 'price' : 'candle';
      this.market$.next({
        data: JSON.stringify({ type, channel, data: payload }),
      });
    });
    this.logger.log('Market SSE relay listening for price:* and candles:*');
  }

  getMarketStream(): Observable<MessageEvent> {
    return this.market$.asObservable();
  }
}

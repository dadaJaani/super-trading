import { Injectable, Logger, OnModuleDestroy, OnModuleInit } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import Redis from 'ioredis';

export type RedisMessageHandler = (channel: string, message: string) => void;

@Injectable()
export class RedisService implements OnModuleInit, OnModuleDestroy {
  private readonly logger = new Logger(RedisService.name);
  private subscriber: Redis | null = null;
  private publisher: Redis | null = null;

  constructor(private readonly configService: ConfigService) {}

  onModuleInit(): void {
    const url = this.configService.get<string>(
      'REDIS_URL',
      'redis://localhost:6379',
    );
    this.subscriber = new Redis(url);
    this.publisher = new Redis(url);
    this.logger.log('Redis clients connected');
  }

  async onModuleDestroy(): Promise<void> {
    await this.subscriber?.quit();
    await this.publisher?.quit();
  }

  async subscribe(
    pattern: string,
    handler: RedisMessageHandler,
  ): Promise<void> {
    if (!this.subscriber) return;

    await this.subscriber.psubscribe(pattern);
    this.subscriber.on('pmessage', (_pattern, channel, message) => {
      handler(channel, message);
    });
    this.logger.log(`Subscribed to Redis pattern: ${pattern}`);
  }

  async publish(channel: string, message: string): Promise<void> {
    await this.publisher?.publish(channel, message);
  }
}

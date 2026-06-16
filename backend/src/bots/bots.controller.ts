import { Controller, Get, NotFoundException, Param } from '@nestjs/common';
import { BotsService } from './bots.service';

@Controller('bots')
export class BotsController {
  constructor(private readonly botsService: BotsService) {}

  @Get()
  findAll() {
    return this.botsService.findAll();
  }

  @Get(':id')
  async findOne(@Param('id') id: string) {
    const bot = await this.botsService.findOne(id);
    if (!bot) {
      throw new NotFoundException(`Bot ${id} not found`);
    }
    return bot;
  }
}
